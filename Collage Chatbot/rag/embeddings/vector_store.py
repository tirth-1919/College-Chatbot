import math
import re
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from datetime import datetime, timezone, UTC, timedelta

class SimpleVectorStore:
    """
    Enhanced hybrid vector & BM25-style keyword search engine with Sentence Transformers support.
    Compatible with SQLite / memory or mapped directly to PostgreSQL pgvector.
    Includes metadata filtering and freshness scoring.
    """
    def __init__(self, use_embeddings: bool = False, model_name: str = "all-MiniLM-L6-v2"):
        self.documents: List[Dict[str, Any]] = []
        self.use_embeddings = use_embeddings
        self.model = None
        self.embeddings_cache: Dict[str, np.ndarray] = {}

        if use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name)
                print(f"[VectorStore] Loaded SentenceTransformer: {model_name}")
            except ImportError:
                print("[VectorStore] sentence-transformers not available, falling back to keyword search")
                self.use_embeddings = False

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any], keywords: str = ""):
        doc_entry = {
            "id": doc_id,
            "content": content,
            "metadata": metadata,
            "keywords": keywords,
            "tokens": self._tokenize(content),
            # Enhanced metadata fields
            "department": metadata.get('department'),
            "course": metadata.get('course'),
            "semester": metadata.get('semester'),
            "subject": metadata.get('subject'),
            "academic_year": metadata.get('academic_year'),
            "source_type": metadata.get('source_type'),
            "event": metadata.get('event'),
            "date": metadata.get('date'),
            "language": metadata.get('language', 'en'),
            "verification_status": metadata.get('verification_status', 'VERIFIED'),
            "freshness_score": metadata.get('freshness_score', 1.0),
            "authority_score": metadata.get('authority_score', 1.0),
            "created_at": metadata.get('created_at', datetime.now(UTC)),
            "updated_at": metadata.get('updated_at', datetime.now(UTC))
        }

        # Generate embedding if enabled
        if self.use_embeddings and self.model:
            try:
                embedding = self.model.encode(content, show_progress_bar=False)
                self.embeddings_cache[doc_id] = embedding
                doc_entry["embedding"] = embedding
            except Exception as e:
                print(f"[VectorStore] Error generating embedding for {doc_id}: {e}")

        self.documents.append(doc_entry)

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b\w+\b', text)]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _calculate_freshness_score(self, doc: Dict[str, Any]) -> float:
        """Calculate freshness score based on document age and updates"""
        freshness = doc.get('freshness_score', 1.0)
        updated_at = doc.get('updated_at')

        if updated_at and isinstance(updated_at, datetime):
            # Decay freshness over time (linear decay over 30 days)
            now = datetime.now(timezone.utc) if updated_at.tzinfo else datetime.now()
            days_old = (now - updated_at).days
            age_factor = max(0.1, 1.0 - (days_old / 30.0))
            freshness = freshness * age_factor

        return freshness

    def _apply_metadata_filters(self, doc: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Apply metadata filters to a document"""
        if not filters:
            return True

        # Department filter
        if filters.get('department') and doc.get('department') != filters['department']:
            return False

        # Course filter
        if filters.get('course') and doc.get('course') != filters['course']:
            return False

        # Semester filter
        if filters.get('semester') is not None and doc.get('semester') != filters['semester']:
            return False

        # Subject filter
        if filters.get('subject') and doc.get('subject') != filters['subject']:
            return False

        # Academic year filter
        if filters.get('academic_year') and doc.get('academic_year') != filters['academic_year']:
            return False

        # Source type filter
        if filters.get('source_type') and doc.get('source_type') != filters['source_type']:
            return False

        # Event filter
        if filters.get('event') and doc.get('event') != filters['event']:
            return False

        # Verification status filter
        if filters.get('verification_status') and doc.get('verification_status') != filters['verification_status']:
            return False

        # Minimum freshness filter
        if filters.get('min_freshness') is not None:
            doc_freshness = self._calculate_freshness_score(doc)
            if doc_freshness < filters['min_freshness']:
                return False

        # Language filter
        if filters.get('language') and doc.get('language') != filters['language']:
            return False

        return True

    def search(self, query: str, top_k: int = 5,
              filters: Optional[Dict[str, Any]] = None,
              enable_freshness_scoring: bool = True) -> List[Tuple[Dict[str, Any], float]]:
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.documents:
            return []

        results = []

        # Generate query embedding if using embeddings
        query_embedding = None
        if self.use_embeddings and self.model:
            try:
                query_embedding = self.model.encode(query, show_progress_bar=False)
            except Exception as e:
                print(f"[VectorStore] Error generating query embedding: {e}")

        for doc in self.documents:
            # Apply metadata filters first
            if not self._apply_metadata_filters(doc, filters):
                continue

            doc_tokens = doc["tokens"]
            if not doc_tokens:
                continue

            # Calculate similarity score
            score = 0.0

            if self.use_embeddings and query_embedding is not None and "embedding" in doc:
                # Use cosine similarity for vector search
                vector_score = self._cosine_similarity(query_embedding, doc["embedding"])
                score = vector_score
            else:
                # Fallback to TF-IDF / Term overlap calculation
                doc_token_set = set(doc_tokens)
                for qt in query_tokens:
                    if qt in doc_token_set:
                        # Term frequency weight
                        tf = doc_tokens.count(qt) / len(doc_tokens)
                        score += 1.0 + (tf * 5.0)

                # Metadata & keyword boost
                keywords_lower = doc.get("keywords", "").lower()
                for qt in query_tokens:
                    if len(qt) > 3 and qt in keywords_lower:
                        score += 1.5

            # Apply freshness and authority scoring
            if enable_freshness_scoring:
                freshness = self._calculate_freshness_score(doc)
                authority = doc.get('authority_score', 1.0)

                # Combined score: base score * freshness * authority
                # But don't let freshness completely override relevance
                score = score * (0.7 + 0.3 * freshness) * (0.8 + 0.2 * authority)

            if score > 0:
                results.append((doc, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete_document(self, doc_id: str):
        """Delete a document by ID"""
        self.documents = [doc for doc in self.documents if doc['id'] != doc_id]
        if doc_id in self.embeddings_cache:
            del self.embeddings_cache[doc_id]

    def update_document(self, doc_id: str, content: str = None, metadata: Dict[str, Any] = None):
        """Update an existing document"""
        for doc in self.documents:
            if doc['id'] == doc_id:
                if content:
                    doc['content'] = content
                    doc['tokens'] = self._tokenize(content)
                    # Regenerate embedding if enabled
                    if self.use_embeddings and self.model:
                        try:
                            embedding = self.model.encode(content, show_progress_bar=False)
                            self.embeddings_cache[doc_id] = embedding
                            doc['embedding'] = embedding
                        except Exception as e:
                            print(f"[VectorStore] Error regenerating embedding: {e}")

                if metadata:
                    doc['metadata'].update(metadata)
                    # Update specific metadata fields
                    for field in ['department', 'course', 'semester', 'subject', 'academic_year',
                                 'source_type', 'event', 'date', 'language', 'verification_status',
                                 'freshness_score', 'authority_score']:
                        if field in metadata:
                            doc[field] = metadata[field]
                    doc['updated_at'] = datetime.now(UTC)
                break

    def get_documents_by_filter(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all documents matching metadata filters"""
        return [doc for doc in self.documents if self._apply_metadata_filters(doc, filters)]

    def get_stale_documents(self, days_threshold: int = 7) -> List[Dict[str, Any]]:
        """Get documents that are considered stale"""
        threshold_date = datetime.now(UTC) - timedelta(days=days_threshold)
        return [
            doc for doc in self.documents
            if doc.get('updated_at') and doc['updated_at'] < threshold_date
        ]
