from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import MLModel, MLDataset, AuditLog

class ModelRegistryManager:
    """Manages versioning, evaluation benchmarks, deployment, and rollback of specialized ML/NN models"""
    
    @staticmethod
    def register_model(
        db: Session,
        name: str,
        task: str,
        version: str,
        accuracy: float,
        f1_score: float,
        model_type: str = "NeuralNetwork",
        model_path: Optional[str] = None,
        activate: bool = False
    ) -> MLModel:
        if activate:
            # Deactivate older active versions for this task
            db.query(MLModel).filter(MLModel.task == task, MLModel.is_active == True).update({"is_active": False})

        model = MLModel(
            name=name,
            task=task,
            version=version,
            model_type=model_type,
            accuracy=accuracy,
            f1_score=f1_score,
            is_active=activate,
            model_path=model_path
        )
        db.add(model)
        
        # Log audit
        audit = AuditLog(
            actor_role="SYSTEM",
            action="REGISTER_ML_MODEL",
            target_entity="MLModel",
            details={
                "model_name": name,
                "version": version,
                "accuracy": accuracy,
                "f1_score": f1_score,
                "activated": activate
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def rollback_model(db: Session, task: str, target_version: str) -> Optional[MLModel]:
        target = db.query(MLModel).filter(MLModel.task == task, MLModel.version == target_version).first()
        if not target:
            return None

        db.query(MLModel).filter(MLModel.task == task, MLModel.is_active == True).update({"is_active": False})
        target.is_active = True
        
        audit = AuditLog(
            actor_role="ADMIN",
            action="ROLLBACK_ML_MODEL",
            target_entity="MLModel",
            details={"task": task, "rolled_back_to_version": target_version}
        )
        db.add(audit)
        db.commit()
        db.refresh(target)
        return target
