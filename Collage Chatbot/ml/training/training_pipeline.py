"""
ML Training Pipeline
Dataset versioning, training jobs, evaluation, model registry with approval workflow
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import hashlib
import logging

logger = logging.getLogger(__name__)


class DatasetManager:
    """Dataset versioning and management"""

    def __init__(self):
        self.datasets = {}
        self.dataset_versions = {}

    def create_dataset(self, name: str, data: List[Dict],
                     metadata: Dict[str, Any] = None) -> str:
        """Create a new dataset version"""
        dataset_id = hashlib.md5(f"{name}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]

        dataset = {
            'id': dataset_id,
            'name': name,
            'data': data,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'version': 1
        }

        self.datasets[dataset_id] = dataset
        return dataset_id

    def validate_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Validate dataset quality"""
        if dataset_id not in self.datasets:
            return {'valid': False, 'error': 'Dataset not found'}

        dataset = self.datasets[dataset_id]
        data = dataset['data']

        validation = {
            'valid': True,
            'total_samples': len(data),
            'missing_values': 0,
            'duplicates': 0,
            'issues': []
        }

        # Check for missing values
        for sample in data:
            for key, value in sample.items():
                if value is None or value == '':
                    validation['missing_values'] += 1

        # Check for duplicates
        seen_hashes = set()
        for sample in data:
            sample_hash = hash(json.dumps(sample, sort_keys=True))
            if sample_hash in seen_hashes:
                validation['duplicates'] += 1
            seen_hashes.add(sample_hash)

        # Overall validation
        if validation['missing_values'] > len(data) * 0.1:
            validation['valid'] = False
            validation['issues'].append('Too many missing values')

        if validation['duplicates'] > len(data) * 0.05:
            validation['valid'] = False
            validation['issues'].append('Too many duplicates')

        return validation

    def split_dataset(self, dataset_id: str, train_ratio: float = 0.7,
                    val_ratio: float = 0.15, test_ratio: float = 0.15) -> Dict[str, Any]:
        """Split dataset into train/validation/test sets"""
        if dataset_id not in self.datasets:
            return {'success': False, 'error': 'Dataset not found'}

        dataset = self.datasets[dataset_id]
        data = dataset['data']

        # Shuffle data
        import random
        random.shuffle(data)

        # Calculate split indices
        train_end = int(len(data) * train_ratio)
        val_end = train_end + int(len(data) * val_ratio)

        splits = {
            'train': data[:train_end],
            'validation': data[train_end:val_end],
            'test': data[val_end:]
        }

        return {
            'success': True,
            'splits': splits,
            'counts': {
                'train': len(splits['train']),
                'validation': len(splits['validation']),
                'test': len(splits['test'])
            }
        }


class ModelRegistry:
    """Model versioning and registry"""

    def __init__(self):
        self.models = {}
        self.model_versions = {}

    def register_model(self, model_name: str, model_data: Any,
                      version: int, metrics: Dict[str, float],
                      metadata: Dict[str, Any] = None) -> str:
        """Register a trained model"""
        model_id = f"{model_name}_v{version}"

        model = {
            'id': model_id,
            'name': model_name,
            'version': version,
            'model_data': model_data,
            'metrics': metrics,
            'metadata': metadata or {},
            'registered_at': datetime.utcnow().isoformat(),
            'status': 'PENDING_APPROVAL'
        }

        self.models[model_id] = model
        return model_id

    def approve_model(self, model_id: str, approved_by: str) -> Dict[str, Any]:
        """Approve a model for deployment"""
        if model_id not in self.models:
            return {'success': False, 'error': 'Model not found'}

        self.models[model_id]['status'] = 'APPROVED'
        self.models[model_id]['approved_by'] = approved_by
        self.models[model_id]['approved_at'] = datetime.utcnow().isoformat()

        return {'success': True, 'message': 'Model approved'}

    def rollback_model(self, model_name: str, target_version: int) -> Dict[str, Any]:
        """Rollback to a previous model version"""
        current_model_id = f"{model_name}_v{target_version + 1}"
        target_model_id = f"{model_name}_v{target_version}"

        if target_model_id not in self.models:
            return {'success': False, 'error': 'Target version not found'}

        # Mark current as superseded
        if current_model_id in self.models:
            self.models[current_model_id]['status'] = 'SUPERSEDED'

        # Mark target as active
        self.models[target_model_id]['status'] = 'ACTIVE'

        return {'success': True, 'message': f'Rolled back to version {target_version}'}


class TrainingPipeline:
    """Complete ML training pipeline"""

    def __init__(self):
        self.dataset_manager = DatasetManager()
        self.model_registry = ModelRegistry()
        self.training_jobs = {}

    def create_training_job(self, dataset_id: str, model_type: str,
                          hyperparameters: Dict[str, Any] = None) -> str:
        """Create a training job"""
        job_id = hashlib.md5(f"{dataset_id}_{model_type}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]

        job = {
            'id': job_id,
            'dataset_id': dataset_id,
            'model_type': model_type,
            'hyperparameters': hyperparameters or {},
            'status': 'PENDING',
            'created_at': datetime.utcnow().isoformat(),
            'started_at': None,
            'completed_at': None,
            'metrics': None
        }

        self.training_jobs[job_id] = job
        return job_id

    def run_training_job(self, job_id: str) -> Dict[str, Any]:
        """Execute a training job"""
        if job_id not in self.training_jobs:
            return {'success': False, 'error': 'Job not found'}

        job = self.training_jobs[job_id]
        job['status'] = 'RUNNING'
        job['started_at'] = datetime.utcnow().isoformat()

        try:
            # Simulate training (in production, actual training would happen here)
            logger.info(f"Running training job {job_id}")

            # Placeholder training
            metrics = {
                'accuracy': 0.85,
                'precision': 0.82,
                'recall': 0.80,
                'f1_score': 0.81
            }

            job['status'] = 'COMPLETED'
            job['completed_at'] = datetime.utcnow().isoformat()
            job['metrics'] = metrics

            return {
                'success': True,
                'job_id': job_id,
                'metrics': metrics
            }
        except Exception as e:
            job['status'] = 'FAILED'
            job['completed_at'] = datetime.utcnow().isoformat()
            job['error'] = str(e)

            logger.error(f"Training job {job_id} failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def evaluate_model(self, model_id: str, test_data: List[Dict]) -> Dict[str, Any]:
        """Evaluate a trained model"""
        if model_id not in self.model_registry.models:
            return {'success': False, 'error': 'Model not found'}

        # Placeholder evaluation
        metrics = {
            'accuracy': 0.87,
            'precision': 0.84,
            'recall': 0.82,
            'f1_score': 0.83,
            'confusion_matrix': [[100, 10], [15, 75]]
        }

        return {
            'success': True,
            'metrics': metrics
        }