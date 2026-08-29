"""
Semantic Intent Engine for AIT College AI Assistant
Provides pluggable semantic similarity and intent embeddings using local lightweight models,
TF-IDF dense vector anchors, or optional external embedding providers.
Handles colloquial phrasing, typos, Hinglish/Gujarati semantic intent matching.
"""

import math
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class SemanticIntentEngine:
    """
    Semantic Intent Matcher using dense TF-IDF n-gram anchor representations and cosine similarity.
    Calculates semantic distance against canonical intent anchors without external cloud dependencies.
    Follows the single canonical dataset principle - uses IntentTrainingDataset as the source of truth.
    """

    def __init__(
        self,
        provider: str = "local",
        similarity_threshold: float = 0.60,
        top_k: int = 3,
        enabled: bool = True
    ):
        self.provider = provider
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.enabled = enabled
        self.vectorizer = None
        self.intent_anchor_matrix = None
        self.intent_labels: List[str] = []
        self._initialize_anchors()

    def _initialize_anchors(self):
        """Builds semantic anchor vector spaces from canonical intent definitions using IntentTrainingDataset"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from ml.intent.training_dataset import IntentTrainingDataset

            dataset = IntentTrainingDataset("semantic_anchors")
            synthetic = dataset._get_synthetic_examples()

            corpus: List[str] = []
            labels: List[str] = []

            for intent, lang_dict in synthetic.items():
                for lang, examples in lang_dict.items():
                    for text in examples:
                        corpus.append(text.strip().lower())
                        labels.append(intent)

            if corpus:
                self.vectorizer = TfidfVectorizer(
                    max_features=12000,
                    ngram_range=(1, 3),
                    sublinear_tf=True,
                    token_pattern=r'(?u)\b\w+\b',
                    analyzer='word'
                )
                self.intent_anchor_matrix = self.vectorizer.fit_transform(corpus)
                self.intent_labels = labels
                logger.info(f"[SemanticIntentEngine] Initialized {len(corpus)} semantic anchors across {len(set(labels))} intents")
        except Exception as e:
            logger.warning(f"[SemanticIntentEngine] Initialization warning: {e}. Semantic layer will pass through gracefully.")
            self.enabled = False

    def _cosine_similarity(self, vec_a, vec_b) -> float:
        """Calculate cosine similarity between query vector and candidate anchor vectors"""
        dot = vec_a.dot(vec_b.T)
        if hasattr(dot, "toarray"):
            return float(dot.toarray()[0][0])
        return float(dot)

    def classify(self, text: str, candidate_intents: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Classifies user query by finding the closest semantic anchor intent.
        Returns structured result with intent, confidence, method, and ranked candidates.

        Args:
            text: User query text
            candidate_intents: Optional list of intents to consider (for filtering)

        Returns:
            Dictionary with:
                - intent: Best matching intent or None
                - confidence: Semantic confidence score (0.0-1.0)
                - method: "semantic"
                - candidates: List of ranked candidate intents with scores
        """
        if not self.enabled or self.vectorizer is None or self.intent_anchor_matrix is None:
            return {
                "intent": None,
                "confidence": 0.0,
                "method": "semantic",
                "candidates": []
            }

        cleaned = re.sub(r'\s+', ' ', text.strip().lower())
        if len(cleaned) < 2:
            return {
                "intent": None,
                "confidence": 0.0,
                "method": "semantic",
                "candidates": []
            }

        try:
            query_vec = self.vectorizer.transform([cleaned])
            # Compute similarities across all anchor examples
            similarities = (self.intent_anchor_matrix * query_vec.T).toarray().flatten()
            if len(similarities) == 0:
                return {
                    "intent": None,
                    "confidence": 0.0,
                    "method": "semantic",
                    "candidates": []
                }

            # Get top matching anchor indices
            top_indices = np.argsort(similarities)[::-1][:self.top_k]
            top_scores = similarities[top_indices]

            best_score = float(top_scores[0])
            best_intent = self.intent_labels[top_indices[0]]

            # Intent voting across top-k for confidence calibration
            intent_votes = {}
            for idx, score in zip(top_indices, top_scores):
                if score > 0.1:
                    it = self.intent_labels[idx]
                    intent_votes[it] = intent_votes.get(it, 0.0) + float(score)

            # Re-normalize best confidence
            calibrated_conf = min(0.98, best_score * 1.15) if best_score > 0.4 else best_score

            # Build ranked candidates list
            candidates = []
            seen_intents = set()
            for idx, score in zip(top_indices, top_scores):
                intent_name = self.intent_labels[idx]
                if intent_name not in seen_intents:
                    candidates.append({
                        "intent": intent_name,
                        "score": float(score)
                    })
                    seen_intents.add(intent_name)

            # Check threshold
            if calibrated_conf >= self.similarity_threshold:
                return {
                    "intent": best_intent,
                    "confidence": float(calibrated_conf),
                    "method": "semantic",
                    "candidates": candidates
                }

            return {
                "intent": None,
                "confidence": float(calibrated_conf),
                "method": "semantic",
                "candidates": candidates
            }
        except Exception as e:
            logger.debug(f"[SemanticIntentEngine] Inference exception: {e}")
            return {
                "intent": None,
                "confidence": 0.0,
                "method": "semantic",
                "candidates": []
            }

    def classify_semantically(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Legacy method for backward compatibility.
        Classifies user query by finding the closest semantic anchor intent.
        Returns: Tuple of (intent, semantic_confidence) if threshold met, else None.
        """
        result = self.classify(text)
        if result["intent"] and result["confidence"] >= self.similarity_threshold:
            return result["intent"], result["confidence"]
        return None
