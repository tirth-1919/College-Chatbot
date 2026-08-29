import io
import re
from typing import Dict, Any, Optional, List
from PIL import Image
import numpy as np

class OCRParser:
    """
    OCR (Optical Character Recognition) parser for scanned/image-based documents.
    Uses Tesseract OCR for text extraction from images and scanned PDFs.
    """
    
    def __init__(self, tesseract_path: Optional[str] = None):
        self.tesseract_path = tesseract_path
        self.tesseract_available = False
        self._check_tesseract_availability()
    
    def _check_tesseract_availability(self):
        """Check if Tesseract OCR is available"""
        try:
            import pytesseract
            if self.tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            
            # Test Tesseract
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            print("[OCRParser] Tesseract OCR is available")
        except ImportError:
            print("[OCRParser] pytesseract not available, OCR disabled")
        except Exception as e:
            print(f"[OCRParser] Tesseract not available: {e}")
    
    def is_ocr_needed(self, pdf_bytes: bytes) -> bool:
        """
        Determine if OCR is needed for a PDF.
        OCR is needed if the PDF contains no extractable text or very little text.
        """
        try:
            from PyPDF2 import PdfReader
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            # Check first few pages for text content
            text_threshold = 100  # Minimum characters to consider text present
            pages_to_check = min(3, len(pdf_reader.pages))
            
            for page_num in range(pages_to_check):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text and len(page_text.strip()) > text_threshold:
                        return False  # Text found, OCR not needed
                except Exception:
                    continue
            
            return True  # No significant text found, OCR needed
            
        except Exception as e:
            print(f"[OCRParser] Error checking if OCR needed: {e}")
            return False  # Assume OCR not needed on error
    
    def perform_ocr(self, image_bytes: bytes, language: str = 'eng') -> Dict[str, Any]:
        """
        Perform OCR on an image.
        
        Args:
            image_bytes: Raw bytes of the image
            language: Language code for OCR (eng, hin, guj, etc.)
            
        Returns:
            Dictionary with OCR results
        """
        if not self.tesseract_available:
            return {
                "success": False,
                "error": "Tesseract OCR not available",
                "text": ""
            }
        
        try:
            import pytesseract
            
            # Open image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Perform OCR
            text = pytesseract.image_to_string(
                processed_image,
                lang=language,
                config='--psm 6'  # Assume uniform block of text
            )
            
            # Get confidence information
            try:
                data = pytesseract.image_to_data(
                    processed_image,
                    lang=language,
                    config='--psm 6',
                    output_type=pytesseract.Output.DICT
                )
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            except Exception:
                avg_confidence = 0
            
            return {
                "success": True,
                "text": text.strip(),
                "confidence": avg_confidence,
                "language": language,
                "word_count": len(text.split()),
                "char_count": len(text)
            }
            
        except Exception as e:
            print(f"[OCRParser] OCR failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }
    
    def perform_ocr_on_pdf(self, pdf_bytes: bytes, language: str = 'eng', 
                         page_range: Optional[tuple] = None) -> Dict[str, Any]:
        """
        Perform OCR on a scanned PDF.
        
        Args:
            pdf_bytes: Raw bytes of the PDF
            language: Language code for OCR
            page_range: Optional tuple (start_page, end_page) for specific pages
            
        Returns:
            Dictionary with OCR results for all pages
        """
        if not self.tesseract_available:
            return {
                "success": False,
                "error": "Tesseract OCR not available",
                "pages": []
            }
        
        try:
            from PyPDF2 import PdfReader
            from pdf2image import convert_from_bytes
            
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            total_pages = len(pdf_reader.pages)
            
            # Determine page range
            if page_range:
                start_page, end_page = page_range
                start_page = max(1, start_page)
                end_page = min(total_pages, end_page)
            else:
                start_page, end_page = 1, total_pages
            
            # Convert PDF pages to images
            print(f"[OCRParser] Converting PDF pages {start_page}-{end_page} to images...")
            images = convert_from_bytes(
                pdf_bytes,
                first_page=start_page,
                last_page=end_page,
                dpi=200  # Higher DPI for better OCR
            )
            
            # Perform OCR on each page
            pages_results = []
            full_text = ""
            
            for page_num, image in enumerate(images, start=start_page):
                print(f"[OCRParser] Performing OCR on page {page_num}...")
                
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Perform OCR
                ocr_result = self.perform_ocr(img_bytes, language)
                
                if ocr_result["success"]:
                    page_result = {
                        "page_number": page_num,
                        "text": ocr_result["text"],
                        "confidence": ocr_result["confidence"],
                        "word_count": ocr_result["word_count"],
                        "char_count": ocr_result["char_count"]
                    }
                    pages_results.append(page_result)
                    full_text += ocr_result["text"] + "\n\n"
                else:
                    pages_results.append({
                        "page_number": page_num,
                        "text": "",
                        "error": ocr_result["error"]
                    })
            
            return {
                "success": True,
                "full_text": full_text.strip(),
                "pages": pages_results,
                "total_pages_processed": len(pages_results),
                "language": language
            }
            
        except ImportError:
            return {
                "success": False,
                "error": "pdf2image not available for PDF OCR conversion",
                "pages": []
            }
        except Exception as e:
            print(f"[OCRParser] PDF OCR failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "pages": []
            }
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results.
        Includes grayscale conversion, noise reduction, and thresholding.
        """
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Convert to numpy array for processing
            img_array = np.array(image)
            
            # Apply thresholding (binarization)
            # This helps with text extraction from noisy images
            threshold = 128
            img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(img_array)
            
            return processed_image
            
        except Exception as e:
            print(f"[OCRParser] Image preprocessing failed: {e}")
            return image  # Return original if preprocessing fails
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        # Common language codes for Tesseract
        return [
            'eng',  # English
            'hin',  # Hindi
            'guj',  # Gujarati
            'san',  # Sanskrit
            'tam',  # Tamil
            'tel',  # Telugu
            'mar',  # Marathi
            'ben',  # Bengali
            'kan',  # Kannada
            'mal',  # Malayalam
            'ori',  # Oriya
            'pan',  # Punjabi
            'urd',  # Urdu
            'ara',  # Arabic
            'chi_sim',  # Chinese Simplified
            'jpn',  # Japanese
            'kor',  # Korean
            'fra',  # French
            'deu',  # German
            'spa',  # Spanish
            'rus',  # Russian
        ]
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text.
        Simple heuristic-based language detection.
        """
        if not text or len(text) < 10:
            return 'eng'  # Default to English
        
        # Check for Hindi characters (Devanagari script)
        if re.search(r'[\u0900-\u097F]', text):
            return 'hin'
        
        # Check for Gujarati characters
        if re.search(r'[\u0A80-\u0AFF]', text):
            return 'guj'
        
        # Default to English for Latin script
        return 'eng'
    
    def combine_ocr_with_text_extraction(self, pdf_bytes: bytes, filename: str = "") -> Dict[str, Any]:
        """
        Smart combination: use text extraction where possible, OCR where needed.
        This provides the best results for mixed PDFs (some pages scanned, some not).
        """
        try:
            from PyPDF2 import PdfReader
            from rag.parsers.pdf_parser import PDFParser
            
            pdf_parser = PDFParser()
            
            # First try normal text extraction
            text_result = pdf_parser.parse_pdf(pdf_bytes, filename)
            
            if text_result["success"]:
                # Check if OCR is needed for any pages
                needs_ocr = self.is_ocr_needed(pdf_bytes)
                
                if not needs_ocr:
                    # Text extraction was sufficient
                    return {
                        "success": True,
                        "method": "text_extraction",
                        "result": text_result,
                        "ocr_performed": False
                    }
                else:
                    # Some pages need OCR
                    print("[OCRParser] Text extraction insufficient, performing OCR...")
                    ocr_result = self.perform_ocr_on_pdf(pdf_bytes)
                    
                    if ocr_result["success"]:
                        # Combine results: use OCR text where text extraction failed
                        combined_text = ""
                        for page in text_result["pages"]:
                            page_num = page["page_number"]
                            if len(page["text"].strip()) < 50:  # Threshold for "empty" page
                                # Use OCR result for this page
                                ocr_page = next((p for p in ocr_result["pages"] if p["page_number"] == page_num), None)
                                if ocr_page and ocr_page["text"]:
                                    combined_text += ocr_page["text"] + "\n\n"
                                else:
                                    combined_text += page["text"] + "\n\n"
                            else:
                                combined_text += page["text"] + "\n\n"
                        
                        return {
                            "success": True,
                            "method": "hybrid",
                            "full_text": combined_text.strip(),
                            "text_extraction_result": text_result,
                            "ocr_result": ocr_result,
                            "ocr_performed": True
                        }
                    else:
                        # OCR failed, fall back to text extraction
                        return {
                            "success": True,
                            "method": "text_extraction_fallback",
                            "result": text_result,
                            "ocr_performed": False,
                            "ocr_error": ocr_result.get("error")
                        }
            else:
                # Text extraction failed completely, try OCR
                print("[OCRParser] Text extraction failed, trying OCR...")
                ocr_result = self.perform_ocr_on_pdf(pdf_bytes)
                
                return {
                    "success": ocr_result["success"],
                    "method": "ocr_only",
                    "result": ocr_result,
                    "ocr_performed": True
                }
                
        except Exception as e:
            print(f"[OCRParser] Combined extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "none"
            }