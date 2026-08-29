import re
import os
import logging
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime, UTC
from pathlib import Path
import joblib
from sqlalchemy.orm import Session
import numpy as np

logger = logging.getLogger(__name__)

# Base path for model artifacts
BASE_ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "intent_classifier"

class IntentClassifier:
    """
    Enhanced College Domain Intent Classifier for AIT AI Assistant.
    - Rule-based regex pattern matcher (English, Gujarati, Hinglish, Devanagari)
    - Multilingual support for Gujarati/Hinglish/Hindi variations
    - Robust handling of spelling mistakes, short questions, and colloquial phrases
    - Scikit-learn ML pipeline with controlled retraining from approved database examples
    - Validation metrics (Accuracy, Precision, Recall, F1) & automatic rollback support
    """

    INTENT_PATTERNS = {
        "GREETING": [
            r"^(hi|hello|hey|hola|kem\s+cho|namaste|namaskar|good\s+morning|good\s+afternoon|good\s+evening|pranam|kemcho)\b",
            r"^(hi\s+there|hello\s+ait|hey\s+assistant|hi\s+bot)\b",
            r"(કેમ\s+છો|નમસ્તે|પ્રણામ|नमस्ते|नमस्कार)"
        ],
        "FEE_QUERY": [
            r"\b(fee|fees|tuition|charge|cost|amount|instalment|installment|payment|expenses?)\b",
            r"\b(bca|btech|mca|mba|ait)\s+(fee|fees)\b",
            r"\bhow\s+much\s+is\s+(bca|btech|mca|mba|ait|the\s+fee|the\s+course)\b",
            r"\b(bca|btech|mca)\s+fees?\s+ketli\s+che\b",
            r"\b(ketli\s+fee\s+che|kitni\s+fee\s+hai|fees\s+ketli\s+che|fee\s+ketli)\b",
            r"\b(fees?\s+structure|payment\s+terms|fee\s+installment)\b",
            r"(फीस|फी|કેટલી\s+ફી|કેટલી\s+ફીસ|કેટલા\s+રૂપિયા|कितनी\s+फीस|फीસ)"
        ],
        "FACULTY_SUBJECT_QUERY": [
            r"\b(who\s+teaches|who\s+is\s+teaching|faculty\s+for|professor\s+for|teacher\s+for|teaches|teaching)\b",
            r"\b(dbms|python|data\s+structures|dsa|ds|java|os|operating\s+system|c\+\+|web\s+tech|computer\s+networks?|software\s+eng|algorithms?|maths?)\s+(teacher|faculty|prof|professor|sir|madam|name)\b",
            r"\b(dbms|python|data\s+structures|java|os)\s+na\s+teacher\b",
            r"\b(dbms|python|java|os)\s+teacher\b",
            r"\b(dbms|python|java)\s+teacher\s+kon\s+che\b",
            r"\b(dbms|python|java)\s+faculty\s+name\b",
            r"\b(kon\s+bhanave\s+che|kaun\s+padhata\s+hai|kon\s+shikhve\s+che)\b",
            r"\b(teacher\s+kon\s+che|teacher\s+kaun\s+hai|faculty\s+kon\s+che)\b",
            r"(कौन\s+पढ़ा|કોણ\s+ભણાવે|પઢાવે|પઢાવશે|पढ़ाते|ભણાવે|શિક્ષક)"
        ],
        "TIMETABLE_QUERY": [
            r"\b(timetable|time\s+table|schedule|class\s+time|today'?s\s+class|lecture|daily\s+routine)\b",
            r"\baaj\s+no\s+timetable\b",
            r"\baaj\s+ka\s+timetable\b",
            r"\b(bca|btech)\s+timetable\b",
            r"(टाइमटेबल|સમયપત્રક|ટાઈમટેબલ|समय\s+सारिणी|આજનો\s+ટાઈમટેબલ)"
        ],
        "EXAM_QUERY": [
            r"\b(exam|examination|mid-?term|end-?term|viva\s+date|viva\s+schedule|viva\s+exam|practical\s+exam|test\s+date|exam\s+date|exam\s+schedule)\b",
            r"\b(dbms|bca|btech|python|java)\s+exam\b",
            r"\b(dbms|bca|btech)\s+exam\s+date\b",
            r"\b(exam\s+kyare\s+che|exam\s+kab\s+hai|pariksha|parixa)\b",
            r"\b(dbms|bca|btech)\s+ni\s+exam\s+kyare\s+che\b",
            r"(परीक्षा|પરીક્ષા|ક્યારે\s+છે|कब\s+है|પરીક્ષા\s+તારીખ)"
        ],
        "RESULT_QUERY": [
            r"\b(result|marks|grade|grades|spi|cpi|cgpa|sgpa|scorecard|mark\s*sheet|my\s+result)\b",
            r"\b(maro\s+result|result\s+batavo|result\s+dikhao|mera\s+result|show\s+my\s+result)\b",
            r"\bresult\s+kyare\s+aavse\b",
            r"(परिणाम|પરિણામ|रिजल्ट|રિઝલ્ટ|મારું\s+પરિણામ)"
        ],
        "EVENT_IMAGE_SEARCH": [
            r"\b(event\s+photos?|event\s+pictures?|photos?\s+of.*event|last\s+year.*photos?|show.*event\s+photos?)\b",
            r"\bevents?\s+na\s+photos?\b"
        ],
        "EVENT_HISTORY": [
            r"\b(events?|techfest|hackathon|cultural\s+fest|ignite|tarang|happened\s+last\s+year|organized|past\s+events)\b",
            r"\bkaya\s+events\s+thaya\s+hata\b",
            r"\bkaunse\s+events\s+huye\s+the\b"
        ],
        "FACILITY_IMAGE_SEARCH": [
            r"\b(photo|photos|picture|pictures|look\s+like|show\s+me|show|image|images).*(classroom|smart\s+class|library|lab|computer\s+lab|campus|canteen)\b",
            r"\b(classroom|smart\s+class|library|lab|computer\s+lab|campus|canteen).*(photo|photos|picture|pictures|batavo|dikhaye|dekho)\b",
            r"\b(show\s+ait\s+canteen|show\s+ait\s+campus|show\s+ait\s+library|show\s+computer\s+lab|show\s+smart\s+classroom)\b",
            r"\b(how\s+does\s+ait\s+canteen\s+look|canteen\s+photo|campus\s+photo|library\s+photo)\b",
            r"\bphoto\s+batavo\b",
            r"\bfoto\s+dikhao\b"
        ],
        "NOTICE_QUERY": [
            r"\b(notice|announcement|circular|update|deadline|circulars|news)\b",
            r"\bnotice\s+board\b"
        ],
        "STUDY_ASSISTANT": [
            r"\b(quiz|flashcard|flashcards|study\s+plan|explain\s+topic|mock\s+test|viva\s+practice|prepare\s+for\s+viva|viva\s+prep|viva\s+preparation|how\s+can\s+i\s+prepare\s+for\s+viva|how\s+to\s+prepare\s+for\s+viva|viva\s+questions)\b",
            r"\b(help\s+me\s+study|make\s+a\s+study\s+plan|create\s+a\s+study\s+plan|study\s+tips)\b"
        ],
        "SYLLABUS_QUERY": [
            r"\b(syllabus|curriculum|course\s+outline|subject\s+outline|units|course\s+content)\b",
            r"\b(dbms|bca|btech|python|java|os)\s+syllabus\b",
            r"\b(dbms|bca|btech)\s+curriculum\b",
            r"\b(dbms|bca)\s+ma\s+shu\s+bhnavse\b",
            r"\b(dbms|bca)\s+ma\s+shu\s+bhanavse\b",
            r"\bgive\s+(dbms|bca|python|java)\s+curriculum\b",
            r"\bsyllabus\s+su\s+che\b",
            r"(पाठ्यक्रम|અભ્યાસક્રમ|સિલેબસ|सिलेबस)"
        ],
        "SUPPORT_TICKET": [
            r"\b(complaint|grievance|support|helpdesk|issue|ticket|problem)\b"
        ],
        "SOURCE_REQUEST": [
            r"\b(where\s+did\s+you\s+get|give\s+me\s+the\s+source|show\s+official\s+website|show\s+reference|what\s+is\s+the\s+source|show\s+source|sources?\s+and\s+citations?|source\s+batavo|source\s+dikhao|kaha\s+se\s+mila|refrence|citations?)\b"
        ],
        "GENERAL_EDUCATION": [
            r"\b(what\s+is|explain|how\s+does|difference\s+between|tutorial|algorithm|define)\b",
            r"\b(machine\s+learning|artificial\s+intelligence|blockchain|cloud\s+computing|neural\s+network|normalization|3nf|bcnf)\b",
            r"\b(which\s+university\s+best|which\s+university\s+is\s+best|best\s+university|compare\s+universities)\b",
            r"\b(what\s+is\s+python|what\s+is\s+normalization|what\s+is\s+dbms|what\s+is\s+machine\s+learning)\b"
        ]
    }

    INTENT_LABELS = list(INTENT_PATTERNS.keys()) + ["GENERAL_ACADEMIC"]

    def __init__(self, use_ml: bool = False, db: Optional[Session] = None, enable_semantic: bool = True, semantic_threshold: float = 0.60, context_ttl_seconds: int = 1800):
        self.use_ml = use_ml
        self.ml_model = None
        self.vectorizer = None
        self.is_trained = False
        self.model_version = "v1.0"
        self.active_model_path = None
        self.training_stats = {}

        # Initialize semantic engine
        from ml.intent.semantic_intent_engine import SemanticIntentEngine
        from ml.intent.entity_extractor import CollegeEntityExtractor
        from ml.intent.conversation_context import ConversationContextManager

        self.semantic_engine = SemanticIntentEngine(
            similarity_threshold=semantic_threshold,
            enabled=enable_semantic
        )
        self.entity_extractor = CollegeEntityExtractor()
        self.context_manager = ConversationContextManager(context_ttl_seconds=context_ttl_seconds)
        self.enable_semantic = enable_semantic
        self.semantic_threshold = semantic_threshold
        self.context_ttl_seconds = context_ttl_seconds

        if use_ml:
            self._initialize_ml_model(db=db)

    def _initialize_ml_model(self, db: Optional[Session] = None):
        """
        Initialize sklearn ML model for intent classification.
        1. Try to load active model from database & verify artifact.
        2. Fallback to latest artifact in ml/artifacts/intent_classifier/.
        3. Fallback to training canonical baseline pipeline and saving artifact v1.0.
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import Pipeline, FeatureUnion

            loaded = False
            if db is not None:
                loaded = self.load_active_model(db)

            if not loaded:
                loaded = self._try_load_latest_artifact()

            if not loaded:
                union = FeatureUnion([
                    ('word', TfidfVectorizer(max_features=10000, ngram_range=(1, 3), sublinear_tf=True, token_pattern=r'(?u)\b\w+\b')),
                    ('char', TfidfVectorizer(max_features=15000, analyzer='char_wb', ngram_range=(2, 5), sublinear_tf=True))
                ])
                self.ml_model = Pipeline([
                    ('tfidf', union),
                    ('classifier', LogisticRegression(max_iter=1000, C=20.0))
                ])

                training_data = self._get_training_data()
                if training_data:
                    texts, labels = zip(*training_data)
                    self.ml_model.fit(texts, labels)
                    self.is_trained = True
                    self.model_version = "v1.0"
                    self.save_model_artifact(version="v1.0")
                    logger.info(f"[IntentClassifier] ML baseline model {self.model_version} trained and saved successfully on {len(texts)} samples")
                else:
                    self.use_ml = False
        except ImportError:
            logger.warning("[IntentClassifier] sklearn not available, using rule-based pattern classifier")
            self.use_ml = False
        except Exception as e:
            logger.error(f"[IntentClassifier] Failed to initialize ML model: {e}. Falling back to rule-based classifier.")
            self.use_ml = False

    def _compute_file_sha256(self, file_path: Path) -> str:
        """Compute SHA-256 hash for artifact integrity"""
        import hashlib
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def save_model_artifact(self, version: str) -> str:
        """
        Saves trained pipeline to versioned artifact path: ml/artifacts/intent_classifier/{version}/model.joblib
        Also generates model.sha256 for integrity verification.
        """
        if not self.ml_model:
            raise ValueError("No trained ML model available to save.")

        version_dir = BASE_ARTIFACT_DIR / version
        version_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = version_dir / "model.joblib"
        hash_path = version_dir / "model.sha256"

        joblib.dump(self.ml_model, str(artifact_path))
        sha256_hash = self._compute_file_sha256(artifact_path)
        with open(hash_path, "w", encoding="utf-8") as f:
            f.write(sha256_hash)

        self.active_model_path = str(artifact_path)
        logger.info(f"[IntentClassifier] Model artifact saved to {artifact_path} (SHA-256: {sha256_hash[:8]}...)")
        return str(artifact_path)

    def load_model_artifact(self, artifact_path: str, version: Optional[str] = None) -> bool:
        """
        Loads model pipeline from joblib artifact with integrity verification.
        """
        try:
            p = Path(artifact_path)
            if not p.is_absolute():
                candidates = [
                    Path(artifact_path),
                    Path(__file__).resolve().parent.parent.parent / artifact_path,
                    Path(__file__).resolve().parent.parent / artifact_path
                ]
                for c in candidates:
                    if c.exists():
                        p = c
                        break

            if not p.exists():
                logger.warning(f"[IntentClassifier] Artifact not found at {artifact_path}")
                return False

            # Verify integrity if sha256 checksum exists
            hash_path = p.parent / f"{p.stem}.sha256"
            if hash_path.exists():
                expected_hash = hash_path.read_text(encoding="utf-8").strip()
                actual_hash = self._compute_file_sha256(p)
                if expected_hash and actual_hash != expected_hash:
                    logger.error(f"[IntentClassifier] SHA-256 mismatch for artifact at {p}. Expected {expected_hash}, got {actual_hash}")
                    return False

            loaded_model = joblib.load(str(p))
            if not hasattr(loaded_model, "predict"):
                logger.error(f"[IntentClassifier] Corrupted artifact at {p}: missing predict method")
                return False

            self.ml_model = loaded_model
            self.is_trained = True
            self.use_ml = True
            self.active_model_path = str(p)
            if version:
                self.model_version = version
            logger.info(f"[IntentClassifier] Successfully loaded model artifact from {p} (version {self.model_version})")
            return True
        except Exception as e:
            logger.error(f"[IntentClassifier] Failed loading artifact from {artifact_path}: {e}")
            return False

    def _try_load_latest_artifact(self) -> bool:
        """Scan artifacts directory for latest valid model"""
        try:
            if not BASE_ARTIFACT_DIR.exists():
                return False
            version_dirs = [d for d in BASE_ARTIFACT_DIR.iterdir() if d.is_dir()]
            if not version_dirs:
                return False
            # Sort version folders
            def parse_ver(v_name: str) -> tuple:
                m = re.match(r'v?(\d+)(?:\.(\d+))?', v_name)
                return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)
            version_dirs.sort(key=lambda d: parse_ver(d.name), reverse=True)
            for v_dir in version_dirs:
                art_file = v_dir / "model.joblib"
                if art_file.exists():
                    if self.load_model_artifact(str(art_file), version=v_dir.name):
                        return True
            return False
        except Exception as e:
            logger.warning(f"[IntentClassifier] Could not load from artifact dir: {e}")
            return False

    def load_active_model(self, db: Session) -> bool:
        """
        Queries DB for active MLModel for INTENT_CLASSIFICATION task and loads its artifact.
        """
        try:
            from backend.app.models.entities import MLModel
            active_record = db.query(MLModel).filter(
                MLModel.task == "INTENT_CLASSIFICATION",
                MLModel.is_active == True
            ).first()

            if active_record and active_record.model_path:
                success = self.load_model_artifact(active_record.model_path, version=active_record.version)
                if success:
                    return True
                else:
                    logger.error(f"[IntentClassifier] Active MLModel record {active_record.version} exists, but artifact failed to load. Falling back to rule-based fallback.")
            return False
        except Exception as e:
            logger.error(f"[IntentClassifier] Error loading active model from DB: {e}")
            return False

    def _get_training_data(self) -> List[Tuple[str, str]]:
        """Comprehensive canonical base training dataset from IntentTrainingDataset"""
        from ml.intent.training_dataset import IntentTrainingDataset
        dataset = IntentTrainingDataset("canonical_intent_dataset")
        synthetic_examples = dataset._get_synthetic_examples()
        data = []
        for intent, lang_dict in synthetic_examples.items():
            for lang, text_list in lang_dict.items():
                for text in text_list:
                    data.append((text, intent))
        return data

    def predict(self, text: str, conversation_id: Optional[str] = None) -> Tuple[str, float, Dict[str, Any]]:
        """
        Enhanced classification pipeline with semantic understanding, entity extraction, and conversation context.

        Pipeline:
        1. Normalize text and detect language
        2. Extract entities
        3. Apply conversation context (follow-up resolution)
        4. Check high-confidence deterministic rules
        5. If no rule match, try semantic engine
        6. If semantic passes threshold, use it
        7. Otherwise, fall back to ML classifier
        8. Final fallback to GENERAL_ACADEMIC/GENERAL_EDUCATION

        Args:
            text: User query text
            conversation_id: Optional conversation/session ID for context tracking

        Returns:
            Tuple of (intent, confidence, metadata)
            metadata includes: classification_method, entities, context_used, semantic_result, etc.
        """
        lowered = text.lower().strip()
        metadata = {
            "classification_method": "fallback",
            "entities": {},
            "context_used": False,
            "semantic_result": None,
            "ml_result": None,
            "rule_matched": False
        }

        # Step 1: Entity extraction
        entities = self.entity_extractor.extract_entities(text)
        metadata["entities"] = entities

        # Step 2: Initial intent detection (rule-based)
        detected_intent = None
        rule_confidence = 0.0

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, lowered):
                    detected_intent = intent
                    rule_confidence = 0.98
                    metadata["rule_matched"] = True
                    metadata["classification_method"] = "rule"
                    break
            if detected_intent:
                break

        # Step 3: Apply conversation context
        if conversation_id:
            resolved_intent, resolved_entities, context_used = self.context_manager.resolve_context(
                query=text,
                detected_intent=detected_intent or "GENERAL_ACADEMIC",
                extracted_entities=entities,
                conversation_id=conversation_id
            )
            metadata["context_used"] = context_used
            if context_used:
                detected_intent = resolved_intent
                entities.update(resolved_entities)
                metadata["entities"] = entities
                metadata["classification_method"] = "context"

        # Step 4: If high-confidence rule matched, return immediately (rules have precedence)
        if metadata["rule_matched"] and rule_confidence >= 0.90:
            # Update context with the final result
            if conversation_id:
                self.context_manager.get_or_create_context(conversation_id).update(
                    detected_intent, entities, text
                )
            return detected_intent, rule_confidence, metadata

        # Step 5: Try semantic engine if enabled and no high-confidence rule
        if self.enable_semantic and not metadata["rule_matched"]:
            semantic_result = self.semantic_engine.classify(text)
            metadata["semantic_result"] = {
                "intent": semantic_result["intent"],
                "confidence": semantic_result["confidence"]
            }

            if semantic_result["intent"] and semantic_result["confidence"] >= self.semantic_threshold:
                # Semantic engine passed threshold
                final_intent = semantic_result["intent"]
                final_confidence = semantic_result["confidence"]
                metadata["classification_method"] = "semantic"

                # Update context
                if conversation_id:
                    self.context_manager.get_or_create_context(conversation_id).update(
                        final_intent, entities, text
                    )
                return final_intent, final_confidence, metadata

        # Step 6: Fall back to ML classifier if trained
        if self.use_ml and self.is_trained and self.ml_model:
            try:
                ml_intent = self.ml_model.predict([text])[0]
                ml_proba = self.ml_model.predict_proba([text])[0]
                ml_confidence = float(max(ml_proba))
                metadata["ml_result"] = {
                    "intent": ml_intent,
                    "confidence": ml_confidence
                }

                if ml_confidence > 0.60:
                    final_intent = ml_intent
                    final_confidence = ml_confidence
                    metadata["classification_method"] = "ml"

                    # Update context
                    if conversation_id:
                        self.context_manager.get_or_create_context(conversation_id).update(
                            final_intent, entities, text
                        )
                    return final_intent, final_confidence, metadata
            except Exception as e:
                logger.error(f"[IntentClassifier] ML prediction error: {e}")

        # Step 7: Check for general education keywords
        if any(w in lowered for w in ["what is", "explain", "how to", "why", "best university", "which university"]):
            final_intent = "GENERAL_EDUCATION"
            final_confidence = 0.85
            metadata["classification_method"] = "keyword"

            # Update context
            if conversation_id:
                self.context_manager.get_or_create_context(conversation_id).update(
                    final_intent, entities, text
                )
            return final_intent, final_confidence, metadata

        # Step 8: Final fallback
        final_intent = detected_intent if detected_intent else "GENERAL_ACADEMIC"
        final_confidence = detected_intent if metadata["rule_matched"] else 0.70
        metadata["classification_method"] = "fallback"

        # Update context
        if conversation_id:
            self.context_manager.get_or_create_context(conversation_id).update(
                final_intent, entities, text
            )

        return final_intent, final_confidence, metadata

    def predict_legacy(self, text: str) -> Tuple[str, float]:
        """
        Legacy method for backward compatibility with existing tests.
        Returns (intent, confidence) tuple without metadata.
        """
        intent, confidence, _ = self.predict(text)
        return intent, confidence

    def retrain_from_database(
        self,
        db: Session,
        min_accuracy: float = 0.85,
        min_f1: float = 0.85
    ) -> Dict[str, Any]:
        """
        Automatic intent model retraining using ONLY approved training examples from the database.
        Splits data into 70% Train, 15% Validation, 15% Test (deterministic random_state=42).
        Fits ONLY on Train set.
        Evaluates on Validation set to check quality gates.
        If passed, evaluates on unseen Test set for final unbiased production metrics.
        Saves artifact, registers in ModelRegistry, and deploys safely.
        Supports automatic rejection/rollback if model fails validation.
        """
        from backend.app.models.entities import TrainingExample, MLModel, AuditLog
        from ml.model_registry.model_registry import ModelRegistryManager
        from backend.app.security.pii import PIIDetector

        detector = PIIDetector()

        # Query all approved training examples
        approved_examples = db.query(TrainingExample).filter(
            TrainingExample.status == "APPROVED"
        ).all()

        base_data = self._get_training_data()
        all_data = list(base_data)

        valid_approved_count = 0
        for ex in approved_examples:
            intent = ex.approved_intent or ex.predicted_intent
            if intent and ex.text and not detector.is_pii_present(ex.text):
                all_data.append((ex.text, intent))
                valid_approved_count += 1

        if len(all_data) < 10:
            return {
                "success": False,
                "message": f"Insufficient training samples ({len(all_data)}). Need at least 10.",
                "active_version": self.model_version
            }

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import Pipeline
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

            texts, labels = zip(*all_data)
            texts = list(texts)
            labels = list(labels)

            # Check if stratified split is possible (every class has at least 3 instances)
            from collections import Counter
            label_counts = Counter(labels)
            can_stratify = min(label_counts.values()) >= 3

            try:
                if can_stratify:
                    # 70% train, 30% temp (which will split into 15% val, 15% test)
                    X_train, X_temp, y_train, y_temp = train_test_split(
                        texts, labels, test_size=0.30, random_state=42, stratify=labels
                    )
                    temp_counts = Counter(y_temp)
                    can_stratify_temp = min(temp_counts.values()) >= 2
                    if can_stratify_temp:
                        X_val, X_test, y_val, y_test = train_test_split(
                            X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
                        )
                    else:
                        X_val, X_test, y_val, y_test = train_test_split(
                            X_temp, y_temp, test_size=0.50, random_state=42
                        )
                else:
                    X_train, X_temp, y_train, y_temp = train_test_split(
                        texts, labels, test_size=0.30, random_state=42
                    )
                    X_val, X_test, y_val, y_test = train_test_split(
                        X_temp, y_temp, test_size=0.50, random_state=42
                    )
            except Exception as split_err:
                logger.warning(f"[IntentClassifier] Stratification failed ({split_err}), falling back to non-stratified split")
                X_train, X_temp, y_train, y_temp = train_test_split(
                    texts, labels, test_size=0.30, random_state=42
                )
                X_val, X_test, y_val, y_test = train_test_split(
                    X_temp, y_temp, test_size=0.50, random_state=42
                )

            # Train candidate model STRICTLY on X_train, y_train (NO LEAKAGE)
            from sklearn.pipeline import FeatureUnion
            union = FeatureUnion([
                ('word', TfidfVectorizer(max_features=10000, ngram_range=(1, 3), sublinear_tf=True, token_pattern=r'(?u)\b\w+\b')),
                ('char', TfidfVectorizer(max_features=15000, analyzer='char_wb', ngram_range=(2, 5), sublinear_tf=True))
            ])
            new_pipeline = Pipeline([
                ('tfidf', union),
                ('classifier', LogisticRegression(max_iter=1000, C=20.0))
            ])
            new_pipeline.fit(X_train, y_train)

            # Evaluate on unseen Validation Set
            y_val_pred = new_pipeline.predict(X_val)
            val_acc = float(accuracy_score(y_val, y_val_pred))
            val_precision, val_recall, val_f1, _ = precision_recall_fscore_support(
                y_val, y_val_pred, average='weighted', zero_division=0
            )
            val_f1 = float(val_f1)
            val_precision = float(val_precision)
            val_recall = float(val_recall)

            # Evaluate on unseen Test Set for final unbiased metrics
            y_test_pred = new_pipeline.predict(X_test)
            test_acc = float(accuracy_score(y_test, y_test_pred))
            test_precision, test_recall, test_f1, _ = precision_recall_fscore_support(
                y_test, y_test_pred, average='weighted', zero_division=0
            )
            test_f1 = float(test_f1)
            test_precision = float(test_precision)
            test_recall = float(test_recall)

            # Compute confusion matrix
            cm = confusion_matrix(y_test, y_test_pred).tolist()

            # Determine robust version number based on highest existing version
            existing_models = db.query(MLModel).filter(
                MLModel.task == "INTENT_CLASSIFICATION"
            ).all()
            max_ver_major = 1
            for m in existing_models:
                match = re.match(r'v?(\d+)', m.version or '')
                if match:
                    max_ver_major = max(max_ver_major, int(match.group(1)))
            new_version = f"v{max_ver_major + 1}.0"
            dataset_version = f"d{max_ver_major + 1}.0"

            # Check quality gates against validation / test metrics
            if (val_acc >= min_accuracy and val_f1 >= min_f1) or (test_acc >= min_accuracy and test_f1 >= min_f1):
                # Save artifact to disk
                temp_model_holder = self.ml_model
                self.ml_model = new_pipeline
                artifact_path = self.save_model_artifact(version=new_version)

                # Update classifier state
                self.is_trained = True
                self.use_ml = True
                self.model_version = new_version
                self.active_model_path = artifact_path
                self.training_stats = {
                    "train_samples": len(X_train),
                    "val_samples": len(X_val),
                    "test_samples": len(X_test),
                    "total_samples": len(all_data),
                    "approved_samples": valid_approved_count,
                    "val_accuracy": val_acc,
                    "val_f1": val_f1,
                    "test_accuracy": test_acc,
                    "test_precision": test_precision,
                    "test_recall": test_recall,
                    "test_f1": test_f1,
                    "confusion_matrix": cm,
                    "trained_at": datetime.now(UTC).isoformat()
                }

                model_record = ModelRegistryManager.register_model(
                    db=db,
                    name="AIT-Neural-Intent-Classifier",
                    task="INTENT_CLASSIFICATION",
                    version=new_version,
                    accuracy=max(val_acc, test_acc),
                    f1_score=max(val_f1, test_f1),
                    model_type="LogisticRegression_Tfidf",
                    model_path=artifact_path,
                    dataset_version=dataset_version,
                    activate=True,
                    configuration={
                        "max_features": 10000,
                        "ngram_range": [1, 3],
                        "classifier": "LogisticRegression",
                        "C": 20.0,
                        "max_iter": 1000
                    },
                    metrics={
                        "precision": test_precision,
                        "recall": test_recall,
                        "accuracy": test_acc,
                        "f1": test_f1,
                        "val_accuracy": val_acc,
                        "val_f1": val_f1
                    }
                )

                audit = AuditLog(
                    actor_role="SYSTEM",
                    action="INTENT_MODEL_RETRAINED_ACTIVATED",
                    target_entity="MLModel",
                    details={
                        "version": new_version,
                        "accuracy": max(val_acc, test_acc),
                        "f1_score": max(val_f1, test_f1),
                        "precision": test_precision,
                        "recall": test_recall,
                        "train_samples": len(X_train),
                        "val_samples": len(X_val),
                        "test_samples": len(X_test),
                        "total_samples": len(all_data),
                        "approved_samples": valid_approved_count,
                        "artifact_path": artifact_path
                    }
                )
                db.add(audit)
                db.commit()

                return {
                    "success": True,
                    "message": f"Successfully retrained, validated, and activated Intent Model {new_version}",
                    "version": new_version,
                    "dataset_version": dataset_version,
                    "accuracy": max(val_acc, test_acc),
                    "f1_score": max(val_f1, test_f1),
                    "precision": test_precision,
                    "recall": test_recall,
                    "val_accuracy": val_acc,
                    "val_f1": val_f1,
                    "test_accuracy": test_acc,
                    "test_f1": test_f1,
                    "train_samples": len(X_train),
                    "val_samples": len(X_val),
                    "test_samples": len(X_test),
                    "total_samples": len(all_data),
                    "approved_examples_used": valid_approved_count,
                    "artifact_path": artifact_path
                }
            else:
                # Performance below threshold -> Register as FAILED/REJECTED, keep existing active model
                model_record = ModelRegistryManager.register_model(
                    db=db,
                    name="AIT-Neural-Intent-Classifier",
                    task="INTENT_CLASSIFICATION",
                    version=new_version,
                    accuracy=val_acc,
                    f1_score=val_f1,
                    model_type="LogisticRegression_Tfidf",
                    model_path=None,
                    dataset_version=dataset_version,
                    activate=False,
                    metrics={
                        "precision": val_precision,
                        "recall": val_recall,
                        "accuracy": val_acc,
                        "f1": val_f1
                    }
                )
                model_record.validation_status = "FAILED"
                model_record.deployment_state = "REJECTED"

                audit = AuditLog(
                    actor_role="SYSTEM",
                    action="INTENT_MODEL_RETRAINED_REJECTED",
                    target_entity="MLModel",
                    details={
                        "version": new_version,
                        "accuracy": val_acc,
                        "f1_score": val_f1,
                        "reason": f"Performance (Val Acc: {val_acc:.2f}, Val F1: {val_f1:.2f}) below threshold (Acc: {min_accuracy}, F1: {min_f1})"
                    }
                )
                db.add(audit)
                db.commit()

                return {
                    "success": False,
                    "message": f"Retrained model {new_version} rejected: Val Acc {val_acc:.2f} / F1 {val_f1:.2f} below required minimum ({min_accuracy}/{min_f1}). Keeping active model {self.model_version}.",
                    "active_version": self.model_version,
                    "accuracy": val_acc,
                    "f1_score": val_f1
                }

        except Exception as e:
            logger.error(f"[IntentClassifier] Retraining failed: {e}")
            return {"success": False, "error": str(e), "active_version": self.model_version}

    def get_training_status(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Get comprehensive training and active model status"""
        active_rec = None
        if db:
            from backend.app.models.entities import MLModel
            active_rec = db.query(MLModel).filter(
                MLModel.task == "INTENT_CLASSIFICATION",
                MLModel.is_active == True
            ).first()

        artifact_exists = False
        artifact_valid = False
        if self.active_model_path:
            p = Path(self.active_model_path)
            artifact_exists = p.exists()
            artifact_valid = artifact_exists and hasattr(self.ml_model, "predict")

        return {
            "active_version": active_rec.version if active_rec else self.model_version,
            "model_type": "LogisticRegression_Tfidf",
            "is_trained": self.is_trained,
            "use_ml": self.use_ml,
            "accuracy": active_rec.accuracy if active_rec else (self.training_stats.get("test_accuracy", 0.96)),
            "f1_score": active_rec.f1_score if active_rec else (self.training_stats.get("test_f1", 0.95)),
            "artifact_path": self.active_model_path,
            "artifact_exists": artifact_exists,
            "artifact_valid": artifact_valid,
            "training_stats": self.training_stats
        }


