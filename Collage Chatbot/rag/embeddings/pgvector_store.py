import math
import re
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy import text, Column, String, Float, Integer, JSON, DateTime
from datetime import datetime, UTC

Base = declarative_base()

class PGVectorDocument(Base):
    """Table for storing documents with pgvector embeddings"""
    __tablename__ = "pgvector_documents"
    
    id = Column(String, primary_key=True)
    content = Column(String, nullable=False)
    embedding = Column(Float, nullable=False)  # Will be stored as array
    doc_metadata = Column(JSON, default=dict)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    keywords = Column(String, nullable=True)
    tokens = Column(JSON, default=list)
    department = Column(String(100), nullable=True)
    course = Column(String(50), nullable=True)
    semester = Column(Integer, nullable=True)
    subject = Column(String(100), nullable=True)
    academic_year = Column(String(20), nullable=True)
    source_type = Column(String(50), nullable=True)
    event = Column(String(200), nullable=True)
    date = Column(String(30), nullable=True)
    language = Column(String(10), default="en")
    verification_status = Column(String(30), default="VERIFIED")
    freshness_score = Column(Float, default=1.0)
    authority_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class PGVectorStore:
    """
    Production PostgreSQL + pgvector store with metadata filtering and freshness scoring.
    Falls back to SimpleVectorStore if pgvector is not available.
    """
    
    def __init__(self, db_session: Optional[Session] = None, use_pgvector: bool = True):
        self.db_session = db_session
        self.use_pgvector = use_pgvector
        self.pgvector_available = False
        self.fallback_store = None
        
        if use_pgvector and db_session:
            self._check_pgvector_availability()
        
        if not self.pgvector_available:
            print("[PGVectorStore] pgvector not available, using fallback SimpleVectorStore")
            from .vector_store import SimpleVectorStore
            self.fallback_store = SimpleVectorStore(use_embeddings=False)
    
    def _check_pgvector_availability(self):
        """Check if pgvector extension is available"""
        try:
            if self.db_session:
                # Try to create the extension if it doesn't exist
                self.db_session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                self.db_session.commit()
                
                # Check if the extension is available
                result = self.db_session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
                if result.fetchone():
                    self.pgvector_available = True
                    print("[PGVectorStore] pgvector extension is available")
                    
                    # Create table if it doesn't exist
                    self._create_pgvector_table()
                else:
                    print("[PGVectorStore] pgvector extension not found")
        except Exception as e:
            print(f"[PGVectorStore] Error checking pgvector availability: {e}")
            self.pgvector_available = False
    
    def _create_pgvector_table(self):
        """Create the pgvector documents table"""
        try:
            # Check if table exists
            result = self.db_session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pgvector_documents'
                )
            """))
            
            if not result.fetchone()[0]:
                # Create table with vector column
                self.db_session.execute(text("""
                    CREATE TABLE pgvector_documents (
                        id VARCHAR PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding VECTOR(1536),
                        metadata JSONB DEFAULT '{}',
                        keywords VARCHAR,
                        tokens JSONB DEFAULT '[]',
                        department VARCHAR(100),
                        course VARCHAR(50),
                        semester INTEGER,
                        subject VARCHAR(100),
                        academic_year VARCHAR(20),
                        source_type VARCHAR(50),
                        event VARCHAR(200),
                        date VARCHAR(30),
                        language VARCHAR(10) DEFAULT 'en',
                        verification_status VARCHAR(30) DEFAULT 'VERIFIED',
                        freshness_score FLOAT DEFAULT 1.0,
                        authority_score FLOAT DEFAULT 1.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes for common filter fields
                self.db_session.execute(text("CREATE INDEX idx_pgvector_dept ON pgvector_documents(department)"))
                self.db_session.execute(text("CREATE INDEX idx_pgvector_course ON pgvector_documents(course)"))
                self.db_session.execute(text("CREATE INDEX idx_pgvector_semester ON pgvector_documents(semester)"))
                self.db_session.execute(text("CREATE INDEX idx_pgvector_subject ON pgvector_documents(subject)"))
                self.db_session.execute(text("CREATE INDEX idx_pgvector_freshness ON pgvector_documents(freshness_score)"))
                
                # Create HNSW index for vector similarity search
                self.db_session.execute(text("""
                    CREATE INDEX idx_pgvector_embedding 
                    ON pgvector_documents 
                    USING hnsw (embedding vector_cosine_ops)
                """))
                
                self.db_session.commit()
                print("[PGVectorStore] Created pgvector_documents table and indexes")
        except Exception as e:
            print(f"[PGVectorStore] Error creating pgvector table: {e}")
            self.db_session.rollback()
    
    def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any], 
                    keywords: str = "", embedding: Optional[np.ndarray] = None):
        """Add a document to the vector store"""
        if self.pgvector_available and self.db_session:
            self._add_pgvector_document(doc_id, content, metadata, keywords, embedding)
        elif self.fallback_store:
            self.fallback_store.add_document(doc_id, content, metadata, keywords)
    
    def _add_pgvector_document(self, doc_id: str, content: str, metadata: Dict[str, Any],
                              keywords: str, embedding: Optional[np.ndarray]):
        """Add document to pgvector table"""
        try:
            # Generate embedding if not provided
            if embedding is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer('all-MiniLM-L6-v2')
                    embedding = model.encode(content, show_progress_bar=False)
                except ImportError:
                    print("[PGVectorStore] sentence-transformers not available, using random embedding")
                    embedding = np.random.rand(1536).astype(np.float32)
            
            # Convert embedding to string format for pgvector
            embedding_str = f"[{','.join(map(str, embedding.tolist()))}]"
            
            # Extract metadata fields
            doc = PGVectorDocument(
                id=doc_id,
                content=content,
                embedding=embedding_str,
                doc_metadata=metadata,
                keywords=keywords,
                tokens=self._tokenize(content),
                department=metadata.get('department'),
                course=metadata.get('course'),
                semester=metadata.get('semester'),
                subject=metadata.get('subject'),
                academic_year=metadata.get('academic_year'),
                source_type=metadata.get('source_type'),
                event=metadata.get('event'),
                date=metadata.get('date'),
                language=metadata.get('language', 'en'),
                verification_status=metadata.get('verification_status', 'VERIFIED'),
                freshness_score=metadata.get('freshness_score', 1.0),
                authority_score=metadata.get('authority_score', 1.0)
            )
            
            self.db_session.merge(doc)
            self.db_session.commit()
            
        except Exception as e:
            print(f"[PGVectorStore] Error adding document: {e}")
            self.db_session.rollback()
    
    def search(self, query: str, top_k: int = 5, 
              filters: Optional[Dict[str, Any]] = None) -> List[Tuple[Dict[str, Any], float]]:
        """Search for similar documents with optional metadata filtering"""
        if self.pgvector_available and self.db_session:
            return self._search_pgvector(query, top_k, filters)
        elif self.fallback_store:
            return self.fallback_store.search(query, top_k)
        return []
    
    def _search_pgvector(self, query: str, top_k: int, 
                        filters: Optional[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float]]:
        """Search using pgvector similarity with metadata filtering"""
        try:
            # Generate query embedding
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                query_embedding = model.encode(query, show_progress_bar=False)
            except ImportError:
                query_embedding = np.random.rand(1536).astype(np.float32)
            
            embedding_str = f"[{','.join(map(str, query_embedding.tolist()))}]"
            
            # Build filter conditions
            filter_conditions = []
            params = {}
            
            if filters:
                if filters.get('department'):
                    filter_conditions.append("department = :department")
                    params['department'] = filters['department']
                if filters.get('course'):
                    filter_conditions.append("course = :course")
                    params['course'] = filters['course']
                if filters.get('semester'):
                    filter_conditions.append("semester = :semester")
                    params['semester'] = filters['semester']
                if filters.get('subject'):
                    filter_conditions.append("subject = :subject")
                    params['subject'] = filters['subject']
                if filters.get('academic_year'):
                    filter_conditions.append("academic_year = :academic_year")
                    params['academic_year'] = filters['academic_year']
                if filters.get('source_type'):
                    filter_conditions.append("source_type = :source_type")
                    params['source_type'] = filters['source_type']
                if filters.get('verification_status'):
                    filter_conditions.append("verification_status = :verification_status")
                    params['verification_status'] = filters['verification_status']
                if filters.get('min_freshness'):
                    filter_conditions.append("freshness_score >= :min_freshness")
                    params['min_freshness'] = filters['min_freshness']
            
            where_clause = " AND ".join(filter_conditions) if filter_conditions else "1=1"
            
            # Execute similarity search with filters
            sql = f"""
                SELECT id, content, doc_metadata, keywords, 
                       1 - (embedding <=> :embedding) as similarity,
                       freshness_score, authority_score,
                       department, course, semester, subject, academic_year,
                       source_type, event, date, language, verification_status
                FROM pgvector_documents
                WHERE {where_clause}
                ORDER BY embedding <=> :embedding
                LIMIT :top_k
            """
            
            params['embedding'] = embedding_str
            params['top_k'] = top_k
            
            result = self.db_session.execute(text(sql), params)
            rows = result.fetchall()
            
            # Convert to results format
            results = []
            for row in rows:
                doc = {
                    'id': row[0],
                    'content': row[1],
                    'doc_metadata': row[2],
                    'keywords': row[3],
                    'freshness_score': row[5],
                    'authority_score': row[6],
                    'department': row[7],
                    'course': row[8],
                    'semester': row[9],
                    'subject': row[10],
                    'academic_year': row[11],
                    'source_type': row[12],
                    'event': row[13],
                    'date': row[14],
                    'language': row[15],
                    'verification_status': row[16]
                }
                
                # Combined score: similarity * freshness * authority
                similarity = row[4]
                freshness = row[5]
                authority = row[6]
                combined_score = similarity * freshness * authority
                
                results.append((doc, combined_score))
            
            return results
            
        except Exception as e:
            print(f"[PGVectorStore] Error in pgvector search: {e}")
            return []
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for storage"""
        return [w.lower() for w in re.findall(r'\b\w+\b', text)]
    
    def delete_document(self, doc_id: str):
        """Delete a document from the store"""
        if self.pgvector_available and self.db_session:
            try:
                self.db_session.execute(
                    text("DELETE FROM pgvector_documents WHERE id = :doc_id"),
                    {'doc_id': doc_id}
                )
                self.db_session.commit()
            except Exception as e:
                print(f"[PGVectorStore] Error deleting document: {e}")
                self.db_session.rollback()
        elif self.fallback_store:
            # Fallback doesn't support deletion directly
            pass
    
    def update_document(self, doc_id: str, content: str = None, 
                       metadata: Dict[str, Any] = None):
        """Update an existing document"""
        if self.pgvector_available and self.db_session:
            try:
                updates = []
                params = {'doc_id': doc_id}
                
                if content:
                    updates.append("content = :content")
                    params['content'] = content
                    # Regenerate embedding
                    try:
                        from sentence_transformers import SentenceTransformer
                        model = SentenceTransformer('all-MiniLM-L6-v2')
                        embedding = model.encode(content, show_progress_bar=False)
                        embedding_str = f"[{','.join(map(str, embedding.tolist()))}]"
                        updates.append("embedding = :embedding")
                        params['embedding'] = embedding_str
                    except ImportError:
                        pass
                
                if metadata:
                    updates.append("doc_metadata = :doc_metadata")
                    params['doc_metadata'] = metadata
                    
                    # Update specific metadata fields
                    if 'department' in metadata:
                        updates.append("department = :department")
                        params['department'] = metadata['department']
                    if 'course' in metadata:
                        updates.append("course = :course")
                        params['course'] = metadata['course']
                    if 'semester' in metadata:
                        updates.append("semester = :semester")
                        params['semester'] = metadata['semester']
                    if 'subject' in metadata:
                        updates.append("subject = :subject")
                        params['subject'] = metadata['subject']
                    if 'freshness_score' in metadata:
                        updates.append("freshness_score = :freshness_score")
                        params['freshness_score'] = metadata['freshness_score']
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                
                if updates:
                    sql = f"UPDATE pgvector_documents SET {', '.join(updates)} WHERE id = :doc_id"
                    self.db_session.execute(text(sql), params)
                    self.db_session.commit()
                    
            except Exception as e:
                print(f"[PGVectorStore] Error updating document: {e}")
                self.db_session.rollback()
    
    def get_document_count(self) -> int:
        """Get total number of documents in the store"""
        if self.pgvector_available and self.db_session:
            try:
                result = self.db_session.execute(text("SELECT COUNT(*) FROM pgvector_documents"))
                return result.fetchone()[0]
            except Exception as e:
                print(f"[PGVectorStore] Error getting document count: {e}")
                return 0
        elif self.fallback_store:
            return len(self.fallback_store.documents)
        return 0
    
    def clear_all(self):
        """Clear all documents from the store"""
        if self.pgvector_available and self.db_session:
            try:
                self.db_session.execute(text("DELETE FROM pgvector_documents"))
                self.db_session.commit()
            except Exception as e:
                print(f"[PGVectorStore] Error clearing documents: {e}")
                self.db_session.rollback()
        elif self.fallback_store:
            self.fallback_store.documents = []