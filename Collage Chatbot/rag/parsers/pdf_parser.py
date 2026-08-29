import io
import hashlib
import re
from typing import Dict, Any, Optional, List
from PyPDF2 import PdfReader

class PDFParser:
    """
    Enhanced PDF document parser for extracting text, metadata, and structure from PDF files.
    Supports detailed page-by-page processing, section tracking, heading detection, and citation support.
    """
    
    def __init__(self):
        self.supported_formats = ['pdf']
    
    def parse_pdf(self, file_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        """
        Parse PDF file and extract text, metadata, and structure with enhanced page/section tracking.
        
        Args:
            file_bytes: Raw bytes of the PDF file
            filename: Original filename of the PDF
            
        Returns:
            Dictionary containing extracted content and metadata with detailed page/section info
        """
        try:
            pdf_file = io.BytesIO(file_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            # Extract basic metadata
            metadata = self._extract_metadata(pdf_reader, filename)
            
            # Extract text from all pages with enhanced tracking
            pages_content = []
            full_text = ""
            sections = []
            headings = []
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        # Enhanced page content with section/heading tracking
                        page_content = {
                            "page_number": page_num + 1,
                            "text": page_text.strip(),
                            "char_count": len(page_text),
                            "word_count": len(page_text.split()),
                            "headings": self._extract_headings(page_text, page_num + 1),
                            "sections": self._extract_page_sections(page_text, page_num + 1)
                        }
                        pages_content.append(page_content)
                        full_text += page_text + "\n\n"
                        
                        # Collect headings and sections from this page
                        headings.extend(page_content["headings"])
                        sections.extend(page_content["sections"])
                        
                except Exception as e:
                    print(f"[PDFParser] Error extracting page {page_num + 1}: {e}")
                    continue
            
            # Clean and structure the extracted text
            clean_text = self._clean_text(full_text)
            
            # Generate content hash
            content_hash = hashlib.sha256(clean_text.encode('utf-8')).hexdigest()
            
            # Extract document-level sections (spanning multiple pages)
            document_sections = self._extract_document_sections(clean_text, pages_content)
            
            return {
                "success": True,
                "filename": filename,
                "format": "pdf",
                "metadata": metadata,
                "full_text": clean_text,
                "content_hash": content_hash,
                "pages": pages_content,
                "total_pages": len(pdf_reader.pages),
                "total_characters": len(clean_text),
                "word_count": len(clean_text.split()),
                "sections": document_sections,
                "headings": headings,
                "page_level_sections": sections,
                "citation_info": self._generate_citation_info(pages_content, metadata)
            }
            
        except Exception as e:
            print(f"[PDFParser] Error parsing PDF: {e}")
            return {
                "success": False,
                "error": str(e),
                "filename": filename
            }
    
    def _extract_metadata(self, pdf_reader: PdfReader, filename: str) -> Dict[str, Any]:
        """Extract metadata from PDF document"""
        metadata = {
            "filename": filename,
            "title": "",
            "author": "",
            "subject": "",
            "creator": "",
            "producer": "",
            "creation_date": "",
            "modification_date": "",
            "page_count": len(pdf_reader.pages)
        }
        
        try:
            pdf_info = pdf_reader.metadata
            if pdf_info:
                metadata.update({
                    "title": pdf_info.get("/Title", ""),
                    "author": pdf_info.get("/Author", ""),
                    "subject": pdf_info.get("/Subject", ""),
                    "creator": pdf_info.get("/Creator", ""),
                    "producer": pdf_info.get("/Producer", ""),
                    "creation_date": str(pdf_info.get("/CreationDate", "")),
                    "modification_date": str(pdf_info.get("/ModDate", ""))
                })
        except Exception as e:
            print(f"[PDFParser] Error extracting metadata: {e}")
        
        return metadata
    
    def _extract_headings(self, page_text: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract headings from a page with hierarchy levels"""
        headings = []
        lines = page_text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Detect heading level based on patterns
            heading_level = None
            
            # All caps headings (usually main headings)
            if line.isupper() and len(line) > 3 and len(line) < 100:
                heading_level = 1
            # Numbered headings (1., 1.1, 1.1.1)
            elif re.match(r'^\d+(\.\d+)*\s+[A-Z]', line):
                depth = line.count('.')
                heading_level = min(depth + 1, 6)
            # Bold/Emphasis patterns (if available in text)
            elif re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:$', line):
                heading_level = 2
            # Markdown-style headers
            elif line.startswith('###'):
                heading_level = 3
            elif line.startswith('##'):
                heading_level = 2
            elif line.startswith('#'):
                heading_level = 1
            
            if heading_level:
                headings.append({
                    "text": line,
                    "level": heading_level,
                    "page_number": page_number,
                    "line_number": line_num + 1,
                    "char_position": page_text.find(line)
                })
        
        return headings
    
    def _extract_page_sections(self, page_text: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract sections from a single page"""
        sections = []
        lines = page_text.split('\n')
        
        current_section = {
            "title": "Untitled",
            "content": "",
            "page_number": page_number,
            "start_line": 0,
            "heading_level": None
        }
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if this line is a heading
            heading_info = self._extract_headings(line, page_number)
            if heading_info:
                # Save previous section if it has content
                if current_section["content"].strip():
                    sections.append(current_section.copy())
                
                # Start new section
                current_section = {
                    "title": line,
                    "content": "",
                    "page_number": page_number,
                    "start_line": line_num + 1,
                    "heading_level": heading_info[0]["level"] if heading_info else None
                }
            else:
                current_section["content"] += line + " "
        
        # Add the last section
        if current_section["content"].strip():
            sections.append(current_section)
        
        return sections
    
    def _extract_document_sections(self, clean_text: str, pages_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract document-level sections that may span multiple pages"""
        sections = []
        
        # Collect all headings across pages
        all_headings = []
        for page in pages_content:
            all_headings.extend(page["headings"])
        
        if not all_headings:
            # No headings found, treat entire document as one section
            return [{
                "title": "Document",
                "content": clean_text,
                "start_page": 1,
                "end_page": len(pages_content),
                "heading_level": None
            }]
        
        # Build sections based on headings
        for i, heading in enumerate(all_headings):
            start_page = heading["page_number"]
            end_page = all_headings[i + 1]["page_number"] - 1 if i + 1 < len(all_headings) else len(pages_content)
            
            # Extract content for this section
            section_content = ""
            for page_num in range(start_page, end_page + 1):
                page_data = next((p for p in pages_content if p["page_number"] == page_num), None)
                if page_data:
                    section_content += page_data["text"] + "\n\n"
            
            sections.append({
                "title": heading["text"],
                "content": section_content.strip(),
                "start_page": start_page,
                "end_page": end_page,
                "heading_level": heading["level"],
                "line_number": heading["line_number"]
            })
        
        return sections
    
    def _generate_citation_info(self, pages_content: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate citation information for the document"""
        return {
            "document_title": metadata.get("title", metadata.get("filename", "Unknown")),
            "author": metadata.get("author", "Unknown"),
            "total_pages": len(pages_content),
            "page_locations": {
                page["page_number"]: {
                    "char_count": page["char_count"],
                    "word_count": page["word_count"],
                    "headings_count": len(page["headings"]),
                    "sections_count": len(page["sections"])
                }
                for page in pages_content
            },
            "citation_format": "PDF",
            "sections_available": len([p for p in pages_content if p["sections"]]) > 0
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove common PDF artifacts
        text = text.replace('\x0c', '')  # Form feed character
        text = text.replace('\x00', '')  # Null character
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove multiple consecutive newlines
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        
        return text.strip()
    
    def extract_page_range(self, file_bytes: bytes, start_page: int, end_page: int) -> Dict[str, Any]:
        """
        Extract text from a specific range of pages with enhanced tracking.
        
        Args:
            file_bytes: Raw bytes of the PDF file
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (1-indexed)
            
        Returns:
            Dictionary containing extracted text from the specified page range with tracking info
        """
        try:
            pdf_file = io.BytesIO(file_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            total_pages = len(pdf_reader.pages)
            start_page = max(1, min(start_page, total_pages))
            end_page = min(end_page, total_pages)
            
            if start_page > end_page:
                start_page, end_page = end_page, start_page
            
            extracted_text = ""
            pages_info = []
            sections = []
            headings = []
            
            for page_num in range(start_page - 1, end_page):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n\n"
                        
                        page_info = {
                            "page_number": page_num + 1,
                            "char_count": len(page_text),
                            "word_count": len(page_text.split()),
                            "headings": self._extract_headings(page_text, page_num + 1),
                            "sections": self._extract_page_sections(page_text, page_num + 1)
                        }
                        pages_info.append(page_info)
                        
                        headings.extend(page_info["headings"])
                        sections.extend(page_info["sections"])
                        
                except Exception as e:
                    print(f"[PDFParser] Error extracting page {page_num + 1}: {e}")
                    continue
            
            return {
                "success": True,
                "text": self._clean_text(extracted_text),
                "pages": pages_info,
                "start_page": start_page,
                "end_page": end_page,
                "total_pages_in_range": len(pages_info),
                "headings": headings,
                "sections": sections
            }
            
        except Exception as e:
            print(f"[PDFParser] Error extracting page range: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_location_info(self, file_bytes: bytes, text_query: str) -> List[Dict[str, Any]]:
        """
        Find page and section locations for a specific text query.
        
        Args:
            file_bytes: Raw bytes of the PDF file
            text_query: Text to search for
            
        Returns:
            List of location information (page, section, heading) where the text was found
        """
        try:
            pdf_file = io.BytesIO(file_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            locations = []
            query_lower = text_query.lower()
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and query_lower in page_text.lower():
                        # Find the context around the match
                        headings = self._extract_headings(page_text, page_num + 1)
                        sections = self._extract_page_sections(page_text, page_num + 1)
                        
                        # Find which section contains the query
                        matching_section = None
                        for section in sections:
                            if query_lower in section["content"].lower():
                                matching_section = section
                                break
                        
                        locations.append({
                            "page_number": page_num + 1,
                            "headings": headings,
                            "section": matching_section,
                            "context_snippet": self._get_context_snippet(page_text, text_query)
                        })
                        
                except Exception as e:
                    print(f"[PDFParser] Error searching page {page_num + 1}: {e}")
                    continue
            
            return locations
            
        except Exception as e:
            print(f"[PDFParser] Error getting location info: {e}")
            return []
    
    def _get_context_snippet(self, text: str, query: str, context_chars: int = 200) -> str:
        """Get context around a query match"""
        query_lower = query.lower()
        text_lower = text.lower()
        match_pos = text_lower.find(query_lower)
        
        if match_pos == -1:
            return ""
        
        start = max(0, match_pos - context_chars)
        end = min(len(text), match_pos + len(query) + context_chars)
        
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def is_supported_format(self, filename: str) -> bool:
        """Check if the file format is supported"""
        return filename.lower().endswith('.pdf')
    
    def validate_pdf(self, file_bytes: bytes):
        """
        Validate if the file is a valid PDF.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            pdf_file = io.BytesIO(file_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            # Try to read the first page to validate
            if len(pdf_reader.pages) > 0:
                first_page = pdf_reader.pages[0]
                first_page.extract_text()  # Try to extract text
                
            return True, ""
            
        except Exception as e:
            return False, f"Invalid PDF file: {str(e)}"