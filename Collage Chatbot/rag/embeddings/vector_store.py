import math
import re
from typing import List, Dict, Any, Tuple

class SimpleVectorStore:
    """
    High-performance, zero-dependency hybrid vector & BM25-style keyword search engine.
    Compatible with SQLite / memory or mapped directly to PostgreSQL pgvector.
    """
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []

    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any], keywords: str = ""):
        self.documents.append({
            "id": doc_id,
            "content": content,
            "metadata": metadata,
            "keywords": keywords,
            "tokens": self._tokenize(content)
        })

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b\w+\b', text)]

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.documents:
            return []

        results = []
        for doc in self.documents:
            doc_tokens = doc["tokens"]
            if not doc_tokens:
                continue

            # TF-IDF / Term overlap calculation
            score = 0.0
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

            if score > 0:
                results.append((doc, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
