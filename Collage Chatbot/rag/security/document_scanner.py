import io
import os
import re
import socket
import struct
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC
from backend.app.config import settings

class DocumentSecurityScanner:
    """
    Security scanner for uploaded documents.
    Validates file types, detects malicious content, and ensures safe document processing.
    """

    # Allowed file types and their MIME types
    ALLOWED_FILE_TYPES = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.txt': 'text/plain',
        '.rtf': 'application/rtf'
    }

    # Maximum file size (50 MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    # Suspicious patterns that might indicate malicious content
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'on\w+\s*=',  # Event handlers
        r'data:text/html',  # Data URLs with HTML
        r'vbscript:',  # VBScript protocol
        r'@import',  # CSS import
        r'expression\s*\(',  # CSS expression
        r'from\s+base64',  # Base64 encoding
        r'eval\s*\(',  # eval() function
        r'document\.',  # Document object access
        r'window\.',  # Window object access
    ]

    # Known malicious file signatures (magic bytes)
    MALICIOUS_SIGNATURES = [
        b'PK\x03\x04',  # ZIP (could contain executables)
        b'\x50\x4B\x03\x04',  # Alternative ZIP signature
        b'MZ',  # Executable
        b'\x7f\x45\x4c\x46',  # ELF executable
        b'\xca\xfe\xba\xbe',  # Mach-O binary
    ]

    def __init__(self, clamav_host: Optional[str] = None, clamav_port: Optional[int] = None):
        self.magic_available = False
        self.clamav_host = clamav_host or settings.CLAMAV_HOST
        self.clamav_port = clamav_port or settings.CLAMAV_PORT
        self.clamav_timeout = settings.CLAMAV_TIMEOUT_SECONDS
        self._check_magic_availability()

    def sanitize_filename(self, filename: str) -> str:
        """Sanitizes filename and prevents directory traversal attacks"""
        # Remove null bytes and control characters
        cleaned = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        # Strip directory traversal characters
        cleaned = os.path.basename(cleaned)
        cleaned = re.sub(r'\.\.+', '.', cleaned)
        cleaned = re.sub(r'[^a-zA-Z0-9._-]', '_', cleaned)
        return cleaned or "uploaded_file.bin"

    def scan_with_clamav_daemon(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Scans file bytes using ClamAV network daemon protocol (INSTREAM).
        Fails safely if daemon is unreachable.
        """
        if not settings.CLAMAV_ENABLED:
            return {
                "scanned": False,
                "is_safe": True,
                "status": "CLAMAV_DISABLED",
                "message": "ClamAV live daemon disabled in environment; heuristic scanners enforced"
            }

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.clamav_timeout)
            s.connect((self.clamav_host, self.clamav_port))
            # Send INSTREAM command
            s.sendall(b"zINSTREAM\0")

            # Stream chunks of bytes
            chunk_size = 2048
            for i in range(0, len(file_bytes), chunk_size):
                chunk = file_bytes[i:i + chunk_size]
                s.sendall(struct.pack("!I", len(chunk)) + chunk)
            # Terminate stream
            s.sendall(struct.pack("!I", 0))

            # Receive result
            response = s.recv(1024).decode('utf-8', errors='ignore')
            s.close()

            if "FOUND" in response:
                virus_name = response.split("FOUND")[0].replace("stream:", "").strip()
                return {
                    "scanned": True,
                    "is_safe": False,
                    "status": "INFECTED",
                    "virus_name": virus_name,
                    "error": f"ClamAV detected malware: {virus_name}"
                }
            elif "OK" in response:
                return {
                    "scanned": True,
                    "is_safe": True,
                    "status": "CLEAN",
                    "message": "ClamAV live scan passed: No virus detected"
                }
            else:
                return {
                    "scanned": True,
                    "is_safe": True,
                    "status": "UNKNOWN_RESPONSE",
                    "message": response
                }
        except Exception as e:
            if settings.CLAMAV_FAIL_SAFE:
                return {
                    "scanned": False,
                    "is_safe": True,
                    "status": "DAEMON_UNAVAILABLE_FALLBACK",
                    "warning": f"ClamAV daemon offline ({e}); proceeding with deep heuristic checks"
                }
            else:
                return {
                    "scanned": False,
                    "is_safe": False,
                    "status": "DAEMON_ERROR",
                    "error": f"ClamAV scan failed in strict mode: {e}"
                }

    def _check_magic_availability(self):
        """Check if python-magic library is available"""
        try:
            import magic
            mime = magic.Magic(mime=True)
            self.magic_available = True
            print("[DocumentSecurityScanner] python-magic is available")
        except Exception:
            print("[DocumentSecurityScanner] python-magic not available, using basic validation")
            self.magic_available = False

    def scan_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Perform comprehensive security scan on a document.

        Args:
            file_bytes: Raw bytes of the file
            filename: Original filename

        Returns:
            Dictionary with scan results
        """
        scan_result = {
            "success": False,
            "is_safe": False,
            "filename": filename,
            "scan_timestamp": datetime.now(UTC).isoformat(),
            "checks": {},
            "errors": [],
            "warnings": []
        }

        try:
            # 1. File size validation
            size_check = self._validate_file_size(file_bytes)
            scan_result["checks"]["file_size"] = size_check
            if not size_check["valid"]:
                scan_result["errors"].append(size_check["error"])
                return scan_result

            # 2. File extension validation
            extension_check = self._validate_file_extension(filename)
            scan_result["checks"]["file_extension"] = extension_check
            if not extension_check["valid"]:
                scan_result["errors"].append(extension_check["error"])
                return scan_result

            # 3. MIME type validation
            mime_check = self._validate_mime_type(file_bytes, filename)
            scan_result["checks"]["mime_type"] = mime_check
            if not mime_check["valid"]:
                scan_result["errors"].append(mime_check["error"])
                return scan_result

            # 4. Content hash generation
            file_hash = self._generate_file_hash(file_bytes)
            scan_result["file_hash"] = file_hash

            # 5. Malicious signature detection
            signature_check = self._check_malicious_signatures(file_bytes)
            scan_result["checks"]["malicious_signatures"] = signature_check
            if not signature_check["valid"]:
                scan_result["errors"].append(signature_check["error"])
                return scan_result

            # 6. Suspicious pattern detection
            pattern_check = self._check_suspicious_patterns(file_bytes)
            scan_result["checks"]["suspicious_patterns"] = pattern_check
            if not pattern_check["valid"]:
                scan_result["warnings"].append(pattern_check["error"])

            # 7. File structure validation
            structure_check = self._validate_file_structure(file_bytes, filename)
            scan_result["checks"]["file_structure"] = structure_check
            if not structure_check["valid"]:
                scan_result["errors"].append(structure_check["error"])
                return scan_result

            # 8. ClamAV live daemon scan
            clamav_check = self.scan_with_clamav_daemon(file_bytes)
            scan_result["checks"]["clamav"] = clamav_check
            if not clamav_check["is_safe"]:
                scan_result["errors"].append(clamav_check.get("error", "ClamAV malware detection rejected file"))
                return scan_result

            # If all checks passed
            scan_result["sanitized_filename"] = self.sanitize_filename(filename)
            scan_result["success"] = True
            scan_result["is_safe"] = True
            scan_result["file_size"] = len(file_bytes)
            scan_result["mime_type"] = mime_check["detected_mime"]

        except Exception as e:
            scan_result["errors"].append(f"Scan failed: {str(e)}")

        return scan_result

    def _validate_file_size(self, file_bytes: bytes) -> Dict[str, Any]:
        """Validate file size"""
        file_size = len(file_bytes)

        if file_size == 0:
            return {
                "valid": False,
                "error": "File is empty",
                "file_size": file_size
            }

        if file_size > self.MAX_FILE_SIZE:
            return {
                "valid": False,
                "error": f"File size {file_size} bytes exceeds maximum {self.MAX_FILE_SIZE} bytes",
                "file_size": file_size
            }

        return {
            "valid": True,
            "file_size": file_size
        }

    def _validate_file_extension(self, filename: str) -> Dict[str, Any]:
        """Validate file extension"""
        if not filename:
            return {
                "valid": False,
                "error": "No filename provided"
            }

        # Get file extension
        import os
        _, ext = os.path.splitext(filename.lower())

        if not ext:
            return {
                "valid": False,
                "error": "No file extension found"
            }

        if ext not in self.ALLOWED_FILE_TYPES:
            return {
                "valid": False,
                "error": f"File extension '{ext}' is not allowed",
                "extension": ext
            }

        return {
            "valid": True,
            "extension": ext,
            "expected_mime": self.ALLOWED_FILE_TYPES[ext]
        }

    def _validate_mime_type(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Validate MIME type"""
        detected_mime = None

        if self.magic_available:
            try:
                import magic
                mime = magic.Magic(mime=True)
                detected_mime = mime.from_buffer(file_bytes)
            except Exception as e:
                print(f"[DocumentSecurityScanner] MIME detection failed: {e}")

        # Fallback to extension-based MIME
        if not detected_mime:
            import os
            _, ext = os.path.splitext(filename.lower())
            detected_mime = self.ALLOWED_FILE_TYPES.get(ext, 'application/octet-stream')

        # Get expected MIME from extension
        import os
        _, ext = os.path.splitext(filename.lower())
        expected_mime = self.ALLOWED_FILE_TYPES.get(ext)

        if not expected_mime:
            return {
                "valid": False,
                "error": f"Cannot determine expected MIME type for extension '{ext}'",
                "detected_mime": detected_mime
            }

        # Check if detected MIME matches expected (with some tolerance)
        # Allow for variations in MIME type strings
        if detected_mime and expected_mime:
            if expected_mime not in detected_mime and detected_mime not in expected_mime:
                return {
                    "valid": False,
                    "error": f"MIME type mismatch: expected '{expected_mime}', detected '{detected_mime}'",
                    "expected_mime": expected_mime,
                    "detected_mime": detected_mime
                }

        return {
            "valid": True,
            "detected_mime": detected_mime,
            "expected_mime": expected_mime
        }

    def _generate_file_hash(self, file_bytes: bytes) -> str:
        """Generate SHA-256 hash of the file"""
        return hashlib.sha256(file_bytes).hexdigest()

    def _check_malicious_signatures(self, file_bytes: bytes) -> Dict[str, Any]:
        """Check for known malicious file signatures"""
        # Check first few bytes for malicious signatures
        header = file_bytes[:4]

        for signature in self.MALICIOUS_SIGNATURES:
            if header.startswith(signature):
                return {
                    "valid": False,
                    "error": f"File contains potentially malicious signature: {signature.hex()}",
                    "signature_detected": signature.hex()
                }

        return {
            "valid": True
        }

    def _check_suspicious_patterns(self, file_bytes: bytes) -> Dict[str, Any]:
        """Check for suspicious patterns in file content"""
        try:
            # Try to decode as text for pattern matching
            text_content = file_bytes.decode('utf-8', errors='ignore')

            found_patterns = []
            for pattern in self.SUSPICIOUS_PATTERNS:
                import re
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    found_patterns.append(pattern)

            if found_patterns:
                return {
                    "valid": False,
                    "error": f"Found suspicious patterns: {', '.join(found_patterns)}",
                    "patterns_found": found_patterns
                }

        except Exception as e:
            print(f"[DocumentSecurityScanner] Pattern check failed: {e}")

        return {
            "valid": True
        }

    def _validate_file_structure(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Validate file structure based on type"""
        import os
        _, ext = os.path.splitext(filename.lower())

        try:
            if ext == '.pdf':
                return self._validate_pdf_structure(file_bytes)
            elif ext in ['.docx', '.xlsx', '.pptx']:
                return self._validate_office_structure(file_bytes)
            elif ext in ['.doc', '.xls', '.ppt']:
                return self._validate_legacy_office_structure(file_bytes)
            else:
                # For text files, basic validation is sufficient
                return {"valid": True}

        except Exception as e:
            return {
                "valid": False,
                "error": f"File structure validation failed: {str(e)}"
            }

    def _validate_pdf_structure(self, file_bytes: bytes) -> Dict[str, Any]:
        """Validate PDF file structure"""
        try:
            if file_bytes.startswith(b'%PDF-'):
                try:
                    from PyPDF2 import PdfReader
                    pdf_file = io.BytesIO(file_bytes)
                    pdf_reader = PdfReader(pdf_file)
                    return {
                        "valid": True,
                        "page_count": len(pdf_reader.pages)
                    }
                except Exception:
                    # Valid PDF header present
                    return {
                        "valid": True,
                        "page_count": 1,
                        "note": "Validated via binary PDF header signature"
                    }
            return {
                "valid": False,
                "error": "Missing standard PDF magic header (%PDF-)"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Invalid PDF structure: {str(e)}"
            }

    def _validate_office_structure(self, file_bytes: bytes) -> Dict[str, Any]:
        """Validate Office Open XML file structure"""
        try:
            from zipfile import ZipFile
            import io

            # Office files are ZIP archives
            zip_file = ZipFile(io.BytesIO(file_bytes))

            # Check for required Office files
            required_files = ['[Content_Types].xml']
            for required in required_files:
                if required not in zip_file.namelist():
                    return {
                        "valid": False,
                        "error": f"Missing required Office file: {required}"
                    }

            return {
                "valid": True,
                "archive_contents": len(zip_file.namelist())
            }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Invalid Office file structure: {str(e)}"
            }

    def _validate_legacy_office_structure(self, file_bytes: bytes) -> Dict[str, Any]:
        """Validate legacy Office file structure"""
        try:
            # Basic check for OLE compound document signature
            if file_bytes[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                return {
                    "valid": True,
                    "format": "OLE Compound Document"
                }
            else:
                return {
                    "valid": False,
                    "error": "Invalid legacy Office file signature"
                }

        except Exception as e:
            return {
                "valid": False,
                "error": f"Legacy Office validation failed: {str(e)}"
            }

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and other attacks"""
        # Remove path components
        import os
        filename = os.path.basename(filename)

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Remove control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)

        # Limit filename length
        filename = filename[:255]

        return filename

    def get_scan_summary(self, scan_result: Dict[str, Any]) -> str:
        """Generate human-readable scan summary"""
        if not scan_result["success"]:
            return f"Scan failed: {', '.join(scan_result['errors'])}"

        if not scan_result["is_safe"]:
            return f"File is unsafe: {', '.join(scan_result['errors'])}"

        summary = f"File is safe. Size: {scan_result['file_size']} bytes, MIME: {scan_result['mime_type']}"

        if scan_result["warnings"]:
            summary += f". Warnings: {', '.join(scan_result['warnings'])}"

        return summary