from datetime import datetime, UTC
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.models.entities import MLModel, MLDataset, AuditLog
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelRegistryManager:
    """
    Enhanced model registry manager with comprehensive versioning, deployment, and rollback support.
    Manages the complete ML model lifecycle including validation, monitoring, and safe rollbacks.
    """

    @staticmethod
    def _verify_artifact_usable(model_path: Optional[str]) -> bool:
        """Verify that a model artifact file exists and can be loaded with joblib"""
        if not model_path:
            return False
        try:
            import joblib
            p = Path(model_path)
            if not p.is_absolute():
                candidates = [
                    Path(model_path),
                    Path(__file__).resolve().parent.parent.parent / model_path,
                    Path(__file__).resolve().parent.parent / model_path
                ]
                for c in candidates:
                    if c.exists():
                        p = c
                        break
            if not p.exists():
                return False
            loaded = joblib.load(str(p))
            return hasattr(loaded, "predict")
        except Exception as e:
            logger.error(f"[ModelRegistry] Artifact at {model_path} failed verification: {e}")
            return False

    @staticmethod
    def register_model(
        db: Session,
        name: str,
        task: str,
        version: str,
        accuracy: float,
        f1_score: float,
        model_type: str = "LogisticRegression_Tfidf",
        model_path: Optional[str] = None,
        dataset_version: Optional[str] = None,
        activate: bool = False,
        configuration: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None
    ) -> MLModel:
        """
        Register a new ML model with comprehensive metadata.
        """
        if activate:
            # Deactivate older active versions for this task
            db.query(MLModel).filter(
                MLModel.task == task,
                MLModel.is_active == True
            ).update({"is_active": False, "deployment_state": "DEACTIVATED"})

            deployment_state = "DEPLOYED"
            validation_status = "VALIDATED"
        else:
            deployment_state = "PENDING"
            validation_status = "PENDING"

        model = MLModel(
            name=name,
            task=task,
            version=version,
            model_type=model_type,
            accuracy=accuracy,
            f1_score=f1_score,
            is_active=activate,
            model_path=model_path,
            dataset_version=dataset_version,
            deployment_state=deployment_state,
            validation_status=validation_status
        )

        db.add(model)
        db.flush()

        # Log comprehensive audit
        audit_details = {
            "model_name": name,
            "version": version,
            "task": task,
            "accuracy": accuracy,
            "f1_score": f1_score,
            "model_type": model_type,
            "model_path": model_path,
            "dataset_version": dataset_version,
            "activated": activate,
            "deployment_state": deployment_state,
            "validation_status": validation_status
        }

        if configuration:
            audit_details["configuration"] = configuration
        if metrics:
            audit_details["metrics"] = metrics

        audit = AuditLog(
            actor_role="SYSTEM",
            action="REGISTER_ML_MODEL",
            target_entity="MLModel",
            details=audit_details
        )
        db.add(audit)
        db.commit()
        db.refresh(model)

        logger.info(f"[ModelRegistry] Registered model {name} v{version} with accuracy {accuracy}")
        return model

    @staticmethod
    def validate_model(
        db: Session,
        model_id: str,
        validation_results: Dict[str, Any],
        passed: bool = True
    ) -> MLModel:
        """
        Update model validation status with detailed results.
        """
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        model.validation_status = "VALIDATED" if passed else "FAILED"
        if not passed:
            model.deployment_state = "REJECTED"

        if "accuracy" in validation_results:
            model.accuracy = validation_results["accuracy"]
        if "f1_score" in validation_results:
            model.f1_score = validation_results["f1_score"]

        audit = AuditLog(
            actor_role="SYSTEM",
            action="VALIDATE_ML_MODEL",
            target_entity="MLModel",
            details={
                "model_id": model_id,
                "model_name": model.name,
                "version": model.version,
                "validation_passed": passed,
                "validation_results": validation_results
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(model)

        logger.info(f"[ModelRegistry] Validated model {model.name} v{model.version}: {model.validation_status}")
        return model

    @staticmethod
    def deploy_model(
        db: Session,
        model_id: str,
        require_validation: bool = True
    ) -> MLModel:
        """
        Deploy a model to production with safety checks.
        Ensures atomic transaction rollback on failure.
        """
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Safety check: require validation
        if require_validation and model.validation_status != "VALIDATED":
            raise ValueError(
                f"Model {model.name} v{model.version} must be validated before deployment. "
                f"Current status: {model.validation_status}"
            )

        # Safety check: verify artifact exists and is loadable if path recorded
        if model.model_path and not ModelRegistryManager._verify_artifact_usable(model.model_path):
            raise ValueError(
                f"Model artifact at {model.model_path} cannot be loaded or is corrupted. Aborting deployment."
            )

        try:
            # Deactivate current active model for this task
            db.query(MLModel).filter(
                MLModel.task == model.task,
                MLModel.is_active == True,
                MLModel.id != model_id
            ).update({
                "is_active": False,
                "deployment_state": "DEACTIVATED"
            })

            # Activate new model
            model.is_active = True
            model.deployment_state = "DEPLOYED"

            # Log deployment audit
            audit = AuditLog(
                actor_role="ADMIN",
                action="DEPLOY_ML_MODEL",
                target_entity="MLModel",
                details={
                    "model_id": model_id,
                    "model_name": model.name,
                    "version": model.version,
                    "task": model.task,
                    "required_validation": require_validation,
                    "model_path": model.model_path
                }
            )
            db.add(audit)
            db.commit()
            db.refresh(model)

            logger.info(f"[ModelRegistry] Deployed model {model.name} v{model.version} to production")
            return model
        except Exception as e:
            db.rollback()
            logger.error(f"[ModelRegistry] Deployment failed, rolled back transaction: {e}")
            raise e

    @staticmethod
    def rollback_model(
        db: Session,
        task: str,
        target_version: str,
        reason: Optional[str] = None
    ) -> MLModel:
        """
        Safe rollback to a previous model version with audit trail.
        Verifies target model artifact integrity before switching active flags.
        """
        if target_version == "previous":
            # Find the most recently deployed or deactivated model before the current one
            target = db.query(MLModel).filter(
                MLModel.task == task,
                MLModel.is_active == False,
                MLModel.validation_status == "VALIDATED"
            ).order_by(MLModel.created_at.desc()).first()
        else:
            target = db.query(MLModel).filter(
                MLModel.task == task,
                MLModel.version == target_version
            ).first()

        if not target:
            raise ValueError(f"Target model version '{target_version}' not found for task '{task}'")

        # Verify target artifact exists and can be loaded if model_path recorded
        if target.model_path and not ModelRegistryManager._verify_artifact_usable(target.model_path):
            raise ValueError(
                f"Cannot rollback to {target.version}: artifact at {target.model_path} is missing or corrupted."
            )

        try:
            # Deactivate current active model
            current_active = db.query(MLModel).filter(
                MLModel.task == task,
                MLModel.is_active == True
            ).first()

            if current_active:
                current_active.is_active = False
                current_active.deployment_state = "ROLLED_BACK"

            # Activate target model
            target.is_active = True
            target.deployment_state = "DEPLOYED"

            # Log comprehensive rollback audit
            audit = AuditLog(
                actor_role="ADMIN",
                action="ROLLBACK_ML_MODEL",
                target_entity="MLModel",
                details={
                    "task": task,
                    "rolled_back_to_version": target.version,
                    "rolled_back_to_model_id": target.id,
                    "previous_active_model": current_active.id if current_active else None,
                    "previous_active_version": current_active.version if current_active else None,
                    "reason": reason or "Manual rollback"
                }
            )
            db.add(audit)
            db.commit()
            db.refresh(target)

            logger.info(
                f"[ModelRegistry] Rolled back {task} from version "
                f"{current_active.version if current_active else 'none'} to {target.version}"
            )
            return target
        except Exception as e:
            db.rollback()
            logger.error(f"[ModelRegistry] Rollback transaction failed: {e}")
            raise e

    @staticmethod
    def get_active_model(db: Session, task: str) -> Optional[MLModel]:
        """Get the currently active model for a task"""
        return db.query(MLModel).filter(
            MLModel.task == task,
            MLModel.is_active == True
        ).first()

    @staticmethod
    def get_model_versions(db: Session, task: str) -> List[MLModel]:
        """Get all versions of a model for a task"""
        return db.query(MLModel).filter(
            MLModel.task == task
        ).order_by(MLModel.created_at.desc()).all()

    @staticmethod
    def get_model_history(db: Session, model_id: str) -> List[AuditLog]:
        """Get audit history for a specific model"""
        return db.query(AuditLog).filter(
            AuditLog.target_entity == "MLModel"
        ).order_by(AuditLog.timestamp.desc()).all()

    @staticmethod
    def compare_models(
        db: Session,
        model_id_1: str,
        model_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two models side by side.
        """
        model_1 = db.query(MLModel).filter(MLModel.id == model_id_1).first()
        model_2 = db.query(MLModel).filter(MLModel.id == model_id_2).first()

        if not model_1 or not model_2:
            raise ValueError("One or both models not found")

        return {
            "model_1": {
                "id": model_1.id,
                "name": model_1.name,
                "version": model_1.version,
                "accuracy": model_1.accuracy,
                "f1_score": model_1.f1_score,
                "is_active": model_1.is_active,
                "deployment_state": model_1.deployment_state,
                "validation_status": model_1.validation_status,
                "created_at": model_1.created_at.isoformat() if model_1.created_at else None
            },
            "model_2": {
                "id": model_2.id,
                "name": model_2.name,
                "version": model_2.version,
                "accuracy": model_2.accuracy,
                "f1_score": model_2.f1_score,
                "is_active": model_2.is_active,
                "deployment_state": model_2.deployment_state,
                "validation_status": model_2.validation_status,
                "created_at": model_2.created_at.isoformat() if model_2.created_at else None
            },
            "comparison": {
                "accuracy_diff": model_1.accuracy - model_2.accuracy,
                "f1_diff": model_1.f1_score - model_2.f1_score,
                "accuracy_improvement": model_1.accuracy > model_2.accuracy,
                "f1_improvement": model_1.f1_score > model_2.f1_score
            }
        }

    @staticmethod
    def get_deployment_candidates(db: Session, task: str) -> List[MLModel]:
        """
        Get models that are validated and ready for deployment.
        """
        return db.query(MLModel).filter(
            MLModel.task == task,
            MLModel.validation_status == "VALIDATED",
            MLModel.is_active == False
        ).order_by(MLModel.accuracy.desc()).all()

    @staticmethod
    def auto_deploy_best_model(
        db: Session,
        task: str,
        min_accuracy_threshold: float = 0.85
    ) -> Optional[MLModel]:
        """
        Automatically deploy the best validated model for a task.
        """
        candidates = ModelRegistryManager.get_deployment_candidates(db, task)

        # Filter by accuracy threshold
        qualified = [m for m in candidates if m.accuracy >= min_accuracy_threshold]

        if not qualified:
            logger.warning(
                f"[ModelRegistry] No qualified models for auto-deployment "
                f"(threshold: {min_accuracy_threshold})"
            )
            return None

        # Select best model by accuracy
        best_model = max(qualified, key=lambda m: m.accuracy)

        try:
            return ModelRegistryManager.deploy_model(db, best_model.id)
        except Exception as e:
            logger.error(f"[ModelRegistry] Auto-deployment failed: {e}")
            return None

