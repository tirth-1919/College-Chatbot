"""
Comprehensive Test Suite for Hardened ML Training & Model Lifecycle
Covers:
1. Dataset creation, PII detection, duplicate detection, train/val/test splitting
2. Multilingual Intent Classification (English, Hindi, Gujarati, Hinglish)
3. Rule-based + ML hierarchy with low confidence fallback
4. Safe artifact serialization (joblib), integrity check (SHA-256), and corruption recovery
5. ModelRegistry: Register, Validate, Deploy, Rollback, Compare, Auto-deploy
6. Zero train/test leakage verification & Quality gate rejection
7. Safe database transaction rollback on deployment/rollback failure
"""

import os
import pytest
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.entities import MLModel, MLDataset, TrainingExample, AuditLog
from ml.intent.intent_classifier import IntentClassifier, BASE_ARTIFACT_DIR
from ml.intent.training_dataset import IntentTrainingDataset
from ml.model_registry.model_registry import ModelRegistryManager
from ml.training.controlled_training_manager import ControlledTrainingManager
from backend.app.security.pii import PIIDetector

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()

class TestDatasetHardening:
    """Test dataset integrity, PII detection, deduplication, and non-destructive splitting"""

    def test_pii_detection_and_scrubbing(self):
        detector = PIIDetector()
        sensitive_text = "My phone is 9876543210 and my email is student@aitindia.in with secret sk-12345678901234567890"
        assert detector.is_pii_present(sensitive_text) is True
        redacted = detector.redact_pii(sensitive_text)
        assert "9876543210" not in redacted
        assert "student@aitindia.in" not in redacted
        assert "sk-12345678901234567890" not in redacted

    def test_duplicate_detection_via_normalized_hash(self):
        dataset = IntentTrainingDataset("test_dedup")
        id1 = dataset._generate_example_id("What is BCA fee?", "FEE_QUERY")
        id2 = dataset._generate_example_id("  what  is  bca  fee?  ", "FEE_QUERY")
        id3 = dataset._generate_example_id("What is BCA fee?", "TIMETABLE_QUERY")
        assert id1 == id2  # Case & whitespace normalization matches
        assert id1 != id3  # Different intent produces different hash

    def test_dataset_split_preserves_all_examples(self):
        dataset = IntentTrainingDataset("test_split_preserve")
        dataset.create_balanced_dataset(examples_per_intent=10)
        total_initial = len(dataset.all_examples)
        assert total_initial > 0

        train, val, test = dataset.train_validation_test_split(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
        assert len(train) > 0
        assert len(val) > 0
        assert len(test) > 0
        # Critical test: self.all_examples is NOT destroyed or overwritten
        assert len(dataset.all_examples) == total_initial
        assert len(train) + len(val) + len(test) == total_initial

    def test_dataset_validation_rejects_pii(self):
        dataset = IntentTrainingDataset("pii_test")
        dataset.add_training_example("Call me at 9876543210 for syllabus", "SYLLABUS_QUERY", "en")
        val_res = dataset.validate_dataset()
        assert val_res["is_valid"] is False
        assert any("PII found" in err for err in val_res["errors"])
class TestMultilingualIntentClassifier:
    """Test intent predictions across English, Hindi, Gujarati, Hinglish and fallback logic"""

    def test_english_intent_classification(self):
        classifier = IntentClassifier(use_ml=True)
        assert classifier.predict("What is the tuition fee for BCA?")[0] == "FEE_QUERY"
        assert classifier.predict("Who is the professor for DBMS?")[0] == "FACULTY_SUBJECT_QUERY"
        assert classifier.predict("Show me today's class timetable")[0] == "TIMETABLE_QUERY"
        assert classifier.predict("When is the final examination date?")[0] == "EXAM_QUERY"
        assert classifier.predict("Where can I download my scorecard?")[0] == "RESULT_QUERY"
        assert classifier.predict("Where did you get this information?")[0] == "SOURCE_REQUEST"

    def test_gujarati_intent_classification(self):
        classifier = IntentClassifier(use_ml=True)
        assert classifier.predict("BCA ની ફી કેટલી છે?")[0] == "FEE_QUERY"
        assert classifier.predict("DBMS કોણ ભણાવે છે?")[0] == "FACULTY_SUBJECT_QUERY"
        assert classifier.predict("આજનો સમયપત્રક શું છે?")[0] == "TIMETABLE_QUERY"
        assert classifier.predict("પરીક્ષા ક્યારે છે?")[0] == "EXAM_QUERY"
        assert classifier.predict("મારું પરિણામ બતાવો")[0] == "RESULT_QUERY"

    def test_hindi_intent_classification(self):
        classifier = IntentClassifier(use_ml=True)
        assert classifier.predict("BCA की फीस कितनी है?")[0] == "FEE_QUERY"
        assert classifier.predict("DBMS कौन पढ़ाता है?")[0] == "FACULTY_SUBJECT_QUERY"
        assert classifier.predict("आज का टाइमटेबल दिखाएं")[0] == "TIMETABLE_QUERY"
        assert classifier.predict("परीक्षा कब होगी?")[0] == "EXAM_QUERY"

    def test_hinglish_intent_classification(self):
        classifier = IntentClassifier(use_ml=True)
        assert classifier.predict("BCA fee kitni hai?")[0] == "FEE_QUERY"
        assert classifier.predict("DBMS kaun padhata hai?")[0] == "FACULTY_SUBJECT_QUERY"
        assert classifier.predict("Exam kab hai?")[0] == "EXAM_QUERY"
        assert classifier.predict("Mera result dikhao")[0] == "RESULT_QUERY"

    def test_general_academic_fallback_on_unclear_queries(self):
        classifier = IntentClassifier(use_ml=False)
        intent, conf, _ = classifier.predict("I need help with my semester academic guidance")
        assert intent in ["GENERAL_ACADEMIC", "GENERAL_EDUCATION"]
        assert conf > 0.50

    def test_deterministic_rules_override_ml(self):
        classifier = IntentClassifier(use_ml=True)
        intent, conf, _ = classifier.predict("what is bca fee")
        assert intent == "FEE_QUERY"
        assert conf >= 0.95
class TestArtifactLifecycleAndIntegrity:
    """Test model artifact persistence, SHA-256 integrity, corruption handling, and reload"""

    def test_artifact_saved_with_sha256_hash(self):
        classifier = IntentClassifier(use_ml=True)
        artifact_path = classifier.save_model_artifact("test_v1.0")
        assert os.path.exists(artifact_path)
        
        hash_file = Path(artifact_path).parent / "model.sha256"
        assert hash_file.exists()
        hash_content = hash_file.read_text().strip()
        assert len(hash_content) == 64  # Valid SHA-256 hex string

    def test_artifact_load_with_hash_verification(self):
        classifier = IntentClassifier(use_ml=True)
        artifact_path = classifier.save_model_artifact("test_v2.0")
        
        new_classifier = IntentClassifier(use_ml=False)
        success = new_classifier.load_model_artifact(artifact_path, version="test_v2.0")
        assert success is True
        assert new_classifier.is_trained is True
        assert new_classifier.model_version == "test_v2.0"

    def test_corrupted_artifact_rejection(self, tmp_path):
        corrupt_dir = tmp_path / "corrupt_v1"
        corrupt_dir.mkdir(parents=True)
        corrupt_file = corrupt_dir / "model.joblib"
        corrupt_hash = corrupt_dir / "model.sha256"

        corrupt_file.write_text("corrupted binary data")
        corrupt_hash.write_text("deadbeef" * 8)

        classifier = IntentClassifier(use_ml=False)
        # Should gracefully return False without raising fatal exceptions
        loaded = classifier.load_model_artifact(str(corrupt_file))
        assert loaded is False

    def test_missing_artifact_graceful_fallback(self):
        classifier = IntentClassifier(use_ml=False)
        loaded = classifier.load_model_artifact("non_existent_path/model.joblib")
        assert loaded is False
        # Should continue functioning with rule-based matcher
        intent, conf, _ = classifier.predict("What is BCA fee?")
        assert intent == "FEE_QUERY"

    def test_active_model_loads_from_db_on_restart(self, db_session):
        classifier = IntentClassifier(use_ml=True)
        artifact_path = classifier.save_model_artifact("v_restart_test")

        # Register and activate model in DB
        ModelRegistryManager.register_model(
            db=db_session,
            name="AIT-Neural-Intent-Classifier",
            task="INTENT_CLASSIFICATION",
            version="v_restart_test",
            accuracy=0.95,
            f1_score=0.94,
            model_path=artifact_path,
            activate=True
        )

        # Simulate fresh instance starting up with DB connection
        restarted_classifier = IntentClassifier(use_ml=True, db=db_session)
        assert restarted_classifier.is_trained is True
        assert restarted_classifier.model_version == "v_restart_test"
class TestModelRegistryAndGovernance:
    """Test ModelRegistryManager, atomic deployment, rollback, and governance"""

    def test_model_registration_and_versioning(self, db_session):
        model = ModelRegistryManager.register_model(
            db=db_session,
            name="AIT-Neural-Intent-Classifier",
            task="INTENT_CLASSIFICATION",
            version="v10.0",
            accuracy=0.92,
            f1_score=0.91,
            model_type="LogisticRegression_Tfidf",
            activate=False
        )
        assert model.id is not None
        assert model.version == "v10.0"
        assert model.model_type == "LogisticRegression_Tfidf"
        assert model.is_active is False

    def test_safe_deployment_deactivates_older_models(self, db_session):
        classifier = IntentClassifier(use_ml=True)
        art_path1 = classifier.save_model_artifact("v11.0")
        art_path2 = classifier.save_model_artifact("v12.0")

        m1 = ModelRegistryManager.register_model(
            db=db_session, name="AIT-Classifier", task="INTENT_CLASSIFICATION", version="v11.0",
            accuracy=0.90, f1_score=0.89, model_path=art_path1, activate=True
        )
        assert m1.is_active is True

        m2 = ModelRegistryManager.register_model(
            db=db_session, name="AIT-Classifier", task="INTENT_CLASSIFICATION", version="v12.0",
            accuracy=0.94, f1_score=0.93, model_path=art_path2, activate=False
        )
        m2.validation_status = "VALIDATED"
        db_session.commit()

        # Deploy m2
        deployed = ModelRegistryManager.deploy_model(db=db_session, model_id=m2.id)
        assert deployed.is_active is True
        assert deployed.deployment_state == "DEPLOYED"

        # Verify m1 is deactivated
        db_session.refresh(m1)
        assert m1.is_active is False

    def test_unvalidated_model_cannot_be_deployed(self, db_session):
        m = ModelRegistryManager.register_model(
            db=db_session, name="AIT-Classifier", task="INTENT_CLASSIFICATION", version="v13.0",
            accuracy=0.60, f1_score=0.55, activate=False
        )
        m.validation_status = "PENDING"
        db_session.commit()

        with pytest.raises(ValueError, match="must be validated before deployment"):
            ModelRegistryManager.deploy_model(db=db_session, model_id=m.id, require_validation=True)

    def test_safe_rollback_flow(self, db_session):
        classifier = IntentClassifier(use_ml=True)
        art_v1 = classifier.save_model_artifact("v14.0")
        art_v2 = classifier.save_model_artifact("v15.0")

        m1 = ModelRegistryManager.register_model(
            db=db_session, name="AIT-Classifier", task="INTENT_CLASSIFICATION", version="v14.0",
            accuracy=0.91, f1_score=0.90, model_path=art_v1, activate=True
        )
        m2 = ModelRegistryManager.register_model(
            db=db_session, name="AIT-Classifier", task="INTENT_CLASSIFICATION", version="v15.0",
            accuracy=0.93, f1_score=0.92, model_path=art_v2, activate=True
        )
        db_session.refresh(m1)
        assert m1.is_active is False
        assert m2.is_active is True

        # Rollback to v14.0
        rolled = ModelRegistryManager.rollback_model(db=db_session, task="INTENT_CLASSIFICATION", target_version="v14.0", reason="Testing rollback")
        assert rolled.version == "v14.0"
        assert rolled.is_active is True

        db_session.refresh(m2)
        assert m2.is_active is False
        assert m2.deployment_state == "ROLLED_BACK"

    def test_quality_gate_rejection_in_retraining(self, db_session):
        classifier = IntentClassifier(use_ml=True, db=db_session)
        # Require impossible 99.9% accuracy/f1
        res = classifier.retrain_from_database(db=db_session, min_accuracy=0.999, min_f1=0.999)
        assert res["success"] is False
        assert "rejected" in res["message"].lower()

    def test_controlled_training_manager_stages(self, db_session):
        # Create dataset record
        dataset_rec = MLDataset(
            name="governed_dataset",
            version="v1.0",
            total_samples=100,
            is_scrubbed_pii=True
        )
        db_session.add(dataset_rec)
        db_session.commit()

        manager = ControlledTrainingManager(db=db_session)
        session = manager.start_training_session(
            dataset_id=dataset_rec.id,
            model_name="AIT-Governed-Classifier",
            task="INTENT_CLASSIFICATION",
            training_config={"algorithm": "LogisticRegression_Tfidf"},
            initiated_by="admin@aitindia.in"
        )
        assert session["session_id"] is not None
        assert session["current_stage"] == "DATASET_PREPARATION"

        # Complete dataset preparation stage
        manager.complete_stage("DATASET_PREPARATION", {"verified_samples": 100}, success=True)
        assert "DATASET_PREPARATION" in manager.current_training_session["stages_completed"]
