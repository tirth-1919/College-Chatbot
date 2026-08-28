import re
from typing import List, Dict, Any

class DocumentChunker:
    """Chunks long official documents and web pages into semantically cohesive passages"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        metadata = metadata or {}
        # Split into sentences
        sentences = re.split(r'(?<=[.?!])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence.split())
            if current_length + sentence_len > self.chunk_size and current_chunk:
                chunk_str = " ".join(current_chunk)
                chunks.append({
                    "content": chunk_str,
                    "chunk_index": len(chunks),
                    "metadata": metadata,
                    "keywords": self._extract_keywords(chunk_str)
                })
                # Maintain overlap
                overlap_count = min(len(current_chunk), 3)
                current_chunk = current_chunk[-overlap_count:]
                current_length = sum(len(s.split()) for s in current_chunk)

            current_chunk.append(sentence)
            current_length += sentence_len

        if current_chunk:
            chunk_str = " ".join(current_chunk)
            chunks.append({
                "content": chunk_str,
                "chunk_index": len(chunks),
                "metadata": metadata,
                "keywords": self._extract_keywords(chunk_str)
            })

        return chunks

    def _extract_keywords(self, text: str) -> str:
        words = re.findall(r'\b[A-Za-z0-9\-\_]{4,}\b', text)
        # Filter common stopwords
        stopwords = {"with", "this", "that", "from", "have", "were", "which", "about", "their", "there", "these", "after"}
        filtered = [w.lower() for w in words if w.lower() not in stopwords]
        # Top unique words
        unique = list(dict.fromkeys(filtered))[:15]
        return ", ".join(unique)
