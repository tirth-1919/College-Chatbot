from datetime import datetime, UTC
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from backend.app.models.entities import MLModel, MLDataset, AuditLog
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ControlledTrainingManager:
    """
    Manages controlled AI training pipeline with comprehensive rollback support.
    Ensures training follows proper governance: Dataset → Training → Evaluation → Approval → Deployment → Rollback.
    CRITICAL: Raw student conversations must NEVER directly become production training data.
    """

    # Training stages
    TRAINING_STAGES = [
        "DATASET_PREPARATION",
        "MODEL_TRAINING",
        "EVALUATION",
        "APPROVAL",
        "DEPLOYMENT",
        "ROLLBACK"
    ]

    def __init__(self, db: Session):
        self.db = db
        self.current_training_session = None

    def start_training_session(
        self,
        dataset_id: str,
        model_name: str,
        task: str,
        training_config: Dict[str, Any],
        initiated_by: str
    ) -> Dict[str, Any]:
        """
        Start a controlled training session with proper governance.

        Args:
            dataset_id: ID of the approved training dataset
            model_name: Name for the new model
            task: Task type (e.g., INTENT_CLASSIFICATION)
            training_config: Training configuration parameters
            initiated_by: User/system initiating training

        Returns:
            Training session information
        """
        # Validate dataset
        dataset = self.db.query(MLDataset).filter(
            MLDataset.id == dataset_id
        ).first()

        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        if not dataset.is_scrubbed_pii:
            raise ValueError(f"Dataset {dataset_id} has not been scrubbed for PII. Training not allowed.")

        # Create training session record
        session_id = f"training_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        self.current_training_session = {
            "session_id": session_id,
            "dataset_id": dataset_id,
            "dataset_version": dataset.version,
            "model_name": model_name,
            "task": task,
            "training_config": training_config,
            "initiated_by": initiated_by,
            "current_stage": "DATASET_PREPARATION",
            "stages_completed": [],
            "stages_failed": [],
            "model_id": None,
            "rollback_available": False,
            "previous_model_id": self._get_current_active_model_id(task),
            "created_at": datetime.now(UTC).isoformat()
        }

        # Log training initiation
        audit = AuditLog(
            actor_id=initiated_by,
            actor_role="ADMIN" if initiated_by != "SYSTEM" else "SYSTEM",
            action="START_TRAINING_SESSION",
            target_entity="MLModel",
            details={
                "session_id": session_id,
                "dataset_id": dataset_id,
                "dataset_version": dataset.version,
                "model_name": model_name,
                "task": task,
                "training_config": training_config,
                "is_scrubbed_pii": dataset.is_scrubbed_pii
            }
        )
        self.db.add(audit)
        self.db.commit()

        logger.info(f"[ControlledTraining] Started training session {session_id}")
        return self.current_training_session

    def complete_stage(
        self,
        stage: str,
        stage_results: Dict[str, Any],
        success: bool = True
    ) -> Dict[str, Any]:
        """
        Mark a training stage as completed or failed.

        Args:
            stage: Training stage name
            stage_results: Results/metrics from the stage
            success: Whether the stage completed successfully

        Returns:
            Updated training session
        """
        if not self.current_training_session:
            raise ValueError("No active training session")

        if stage not in self.TRAINING_STAGES:
            raise ValueError(f"Invalid stage: {stage}")

        if success:
            self.current_training_session["stages_completed"].append(stage)
            self.current_training_session["current_stage"] = self.TRAINING_STAGES[
                self.TRAINING_STAGES.index(stage) + 1
            ] if stage != self.TRAINING_STAGES[-1] else stage
        else:
            self.current_training_session["stages_failed"].append(stage)
            self.current_training_session["current_stage"] = f"FAILED_AT_{stage}"

        # Log stage completion
        audit = AuditLog(
            actor_role="SYSTEM",
            action=f"TRAINING_STAGE_{stage}_{'SUCCESS' if success else 'FAILED'}",
            target_entity="MLModel",
            details={
                "session_id": self.current_training_session["session_id"],
                "stage": stage,
                "success": success,
                "stage_results": stage_results
            }
        )
        self.db.add(audit)
        self.db.commit()

        logger.info(f"[ControlledTraining] Stage {stage} {'completed' if success else 'failed'}")
        return self.current_training_session

    def register_trained_model(
        self,
        model_path: str,
        accuracy: float,
        f1_score: float,
        additional_metrics: Dict[str, float]
    ) -> MLModel:
        """
        Register the trained model after successful training.

        Args:
            model_path: Path to model artifacts
            accuracy: Model accuracy
            f1_score: Model F1 score
            additional_metrics: Additional evaluation metrics

        Returns:
            Registered MLModel
        """
        if not self.current_training_session:
            raise ValueError("No active training session")

        if "MODEL_TRAINING" not in self.current_training_session["stages_completed"]:
            raise ValueError("Model training stage not completed")

        # Create model version based on existing versions
        existing_models = self.db.query(MLModel).filter(
            MLModel.task == self.current_training_session["task"]
        ).all()

        import re
        max_ver_major = 1
        for m in existing_models:
            match = re.match(r'v?(\d+)', m.version or '')
            if match:
                max_ver_major = max(max_ver_major, int(match.group(1)))
        model_version = f"v{max_ver_major + 1}.0"

        # Register model
        from ml.model_registry.model_registry import ModelRegistryManager
        model = ModelRegistryManager.register_model(
            db=self.db,
            name=self.current_training_session["model_name"],
            task=self.current_training_session["task"],
            version=model_version,
            accuracy=accuracy,
            f1_score=f1_score,
            model_type="LogisticRegression_Tfidf",
            model_path=model_path,
            dataset_version=self.current_training_session["dataset_version"],
            activate=False,  # Don't activate until approved
            configuration=self.current_training_session["training_config"],
            metrics=additional_metrics
        )

        self.current_training_session["model_id"] = model.id
        self.current_training_session["rollback_available"] = True

        logger.info(f"[ControlledTraining] Registered model {model.id} with accuracy {accuracy}")
        return model

    def evaluate_model(
        self,
        model_id: str,
        evaluation_results: Dict[str, Any],
        passed: bool,
        evaluated_by: str
    ) -> MLModel:
        """
        Evaluate the trained model and record results.

        Args:
            model_id: Model ID to evaluate
            evaluation_results: Evaluation metrics
            passed: Whether evaluation passed
            evaluated_by: Person/system performing evaluation

        Returns:
            Updated MLModel
        """
        from ml.model_registry.model_registry import ModelRegistryManager

        model = ModelRegistryManager.validate_model(
            db=self.db,
            model_id=model_id,
            validation_results=evaluation_results,
            passed=passed
        )

        # Update training session
        if self.current_training_session:
            self.current_training_session["evaluation_passed"] = passed
            self.current_training_session["evaluation_results"] = evaluation_results

        # Log evaluation
        audit = AuditLog(
            actor_id=evaluated_by,
            actor_role="ADMIN" if evaluated_by != "SYSTEM" else "SYSTEM",
            action="EVALUATE_TRAINED_MODEL",
            target_entity="MLModel",
            details={
                "model_id": model_id,
                "evaluation_passed": passed,
                "evaluation_results": evaluation_results,
                "evaluated_by": evaluated_by
            }
        )
        self.db.add(audit)
        self.db.commit()

        logger.info(f"[ControlledTraining] Model {model_id} evaluation: {'PASSED' if passed else 'FAILED'}")
        return model

    def approve_model(
        self,
        model_id: str,
        approved_by: str,
        approval_notes: Optional[str] = None
    ) -> MLModel:
        """
        Approve a trained model for deployment.

        Args:
            model_id: Model ID to approve
            approved_by: Person approving the model
            approval_notes: Notes about approval

        Returns:
            Approved MLModel
        """
        model = self.db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        if model.validation_status != "VALIDATED":
            raise ValueError(f"Model {model_id} must be validated before approval")

        # Update training session
        if self.current_training_session:
            self.current_training_session["approved"] = True
            self.current_training_session["approved_by"] = approved_by
            self.current_training_session["approval_notes"] = approval_notes

        # Log approval
        audit = AuditLog(
            actor_id=approved_by,
            actor_role="ADMIN",
            action="APPROVE_MODEL_DEPLOYMENT",
            target_entity="MLModel",
            details={
                "model_id": model_id,
                "approved_by": approved_by,
                "approval_notes": approval_notes,
                "dataset_version": model.dataset_version
            }
        )
        self.db.add(audit)
        self.db.commit()

        logger.info(f"[ControlledTraining] Model {model_id} approved by {approved_by}")
        return model

    def deploy_approved_model(
        self,
        model_id: str,
        deployed_by: str
    ) -> MLModel:
        """
        Deploy an approved model to production.

        Args:
            model_id: Model ID to deploy
            deployed_by: Person deploying the model

        Returns:
            Deployed MLModel
        """
        from ml.model_registry.model_registry import ModelRegistryManager

        model = ModelRegistryManager.deploy_model(
            db=self.db,
            model_id=model_id,
            require_validation=True
        )

        # Update training session
        if self.current_training_session:
            self.current_training_session["deployed"] = True
            self.current_training_session["deployed_by"] = deployed_by
            self.current_training_session["deployment_timestamp"] = datetime.now(UTC).isoformat()

        # Log deployment
        audit = AuditLog(
            actor_id=deployed_by,
            actor_role="ADMIN",
            action="DEPLOY_APPROVED_MODEL",
            target_entity="MLModel",
            details={
                "model_id": model_id,
                "deployed_by": deployed_by,
                "previous_model_id": self.current_training_session.get("previous_model_id") if self.current_training_session else None
            }
        )
        self.db.add(audit)
        self.db.commit()

        logger.info(f"[ControlledTraining] Model {model_id} deployed by {deployed_by}")
        return model

    def rollback_training(
        self,
        reason: str,
        rolled_back_by: str,
        rollback_to_previous: bool = True
    ) -> Dict[str, Any]:
        """
        Rollback a failed or problematic training deployment.

        Args:
            reason: Reason for rollback
            rolled_back_by: Person performing rollback
            rollback_to_previous: Whether to rollback to previous model

        Returns:
            Rollback information
        """
        if not self.current_training_session:
            raise ValueError("No active training session to rollback")

        rollback_info = {
            "session_id": self.current_training_session["session_id"],
            "reason": reason,
            "rolled_back_by": rolled_back_by,
            "rollback_timestamp": datetime.now(UTC).isoformat(),
            "previous_model_id": self.current_training_session.get("previous_model_id"),
            "current_model_id": self.current_training_session.get("model_id"),
            "dataset_id": self.current_training_session.get("dataset_id"),
            "stages_completed": self.current_training_session.get("stages_completed", []),
            "stages_failed": self.current_training_session.get("stages_failed", [])
        }

        # Perform actual model rollback if needed
        if rollback_to_previous and self.current_training_session.get("previous_model_id"):
            from ml.model_registry.model_registry import ModelRegistryManager

            try:
                previous_model = ModelRegistryManager.rollback_model(
                    db=self.db,
                    task=self.current_training_session["task"],
                    target_version="previous",  # This would need actual version lookup
                    reason=reason
                )
                rollback_info["successful_rollback"] = True
                rollback_info["rolled_back_to_model"] = previous_model.id
            except Exception as e:
                rollback_info["successful_rollback"] = False
                rollback_info["rollback_error"] = str(e)
                logger.error(f"[ControlledTraining] Model rollback failed: {e}")

        # Mark current model as failed if it exists
        if self.current_training_session.get("model_id"):
            current_model = self.db.query(MLModel).filter(
                MLModel.id == self.current_training_session["model_id"]
            ).first()

            if current_model:
                current_model.deployment_state = "ROLLED_BACK"
                current_model.is_active = False

        # Log rollback
        audit = AuditLog(
            actor_id=rolled_back_by,
            actor_role="ADMIN",
            action="ROLLBACK_TRAINING_DEPLOYMENT",
            target_entity="MLModel",
            details=rollback_info
        )
        self.db.add(audit)
        self.db.commit()

        logger.warning(f"[ControlledTraining] Training rollback performed: {reason}")
        return rollback_info

    def _get_current_active_model_id(self, task: str) -> Optional[str]:
        """Get the current active model ID for a task"""
        from ml.model_registry.model_registry import ModelRegistryManager
        model = ModelRegistryManager.get_active_model(self.db, task)
        return model.id if model else None

    def get_training_session_summary(self) -> Dict[str, Any]:
        """Get summary of the current training session"""
        if not self.current_training_session:
            return {"error": "No active training session"}

        return {
            "session_id": self.current_training_session["session_id"],
            "model_name": self.current_training_session["model_name"],
            "task": self.current_training_session["task"],
            "current_stage": self.current_training_session["current_stage"],
            "stages_completed": self.current_training_session["stages_completed"],
            "stages_failed": self.current_training_session["stages_failed"],
            "dataset_id": self.current_training_session["dataset_id"],
            "dataset_version": self.current_training_session["dataset_version"],
            "model_id": self.current_training_session.get("model_id"),
            "rollback_available": self.current_training_session["rollback_available"],
            "created_at": self.current_training_session["created_at"]
        }

    def validate_training_data(self, dataset_id: str) -> Dict[str, Any]:
        """
        Validate that training data is safe and controlled.

        Args:
            dataset_id: Dataset ID to validate

        Returns:
            Validation results
        """
        dataset = self.db.query(MLDataset).filter(
            MLDataset.id == dataset_id
        ).first()

        if not dataset:
            return {
                "valid": False,
                "error": "Dataset not found"
            }

        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # CRITICAL: Check PII scrubbing
        if not dataset.is_scrubbed_pii:
            validation_results["valid"] = False
            validation_results["errors"].append(
                "Dataset has not been scrubbed for PII. This violates data governance policies."
            )

        # Check data source
        if hasattr(dataset, 'data_source') and dataset.data_source and "raw_student_conversations" in dataset.data_source.lower():
            validation_results["valid"] = False
            validation_results["errors"].append(
                "Dataset contains raw student conversations. This violates data governance policies."
            )

        # Check dataset age
        if dataset.created_at:
            created_at = dataset.created_at.replace(tzinfo=UTC) if dataset.created_at.tzinfo is None else dataset.created_at
            dataset_age = (datetime.now(UTC) - created_at).days
            if dataset_age > 365:
                validation_results["warnings"].append(
                    f"Dataset is {dataset_age} days old. Consider refreshing."
                )

        return validation_results

    def get_training_pipeline_status(self) -> Dict[str, Any]:
        """Get overall training pipeline status"""
        active_models = self.db.query(MLModel).filter(
            MLModel.is_active == True
        ).all()

        pending_models = self.db.query(MLModel).filter(
            MLModel.deployment_state == "PENDING"
        ).all()

        failed_models = self.db.query(MLModel).filter(
            MLModel.validation_status == "FAILED"
        ).all()

        return {
            "active_models": len(active_models),
            "pending_models": len(pending_models),
            "failed_models": len(failed_models),
            "current_session": self.get_training_session_summary(),
            "pipeline_health": "HEALTHY" if len(failed_models) == 0 else "NEEDS_ATTENTION"
        }