"""
File Upload Security Validator for AIT AI Assistant
Validates file uploads for security: extensions, MIME types, content, size
"""

import os
import hashlib
import re
from typing import Optional, Tuple, List
from fastapi import UploadFile, HTTPException, status
import logging

logger = logging.getLogger(__name__)


class FileSecurityValidator:
    """
    Comprehensive file upload security validation
    """

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.ppt', '.pptx',
        '.xls', '.xlsx', '.txt', '.md', '.csv',
        '.jpg', '.jpeg', '.png', '.gif', '.webp'
    }

    # MIME type mappings (used when python-magic is available)
    ALLOWED_MIME_TYPES = {
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-powerpoint': '.ppt',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'text/plain': '.txt',
        'text/markdown': '.md',
        'text/csv': '.csv',
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp'
    }

    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    # Dangerous filename patterns
    DANGEROUS_PATTERNS = [
        '../', '..\\', './', '.\\',  # Path traversal
        '\\x00',  # Null bytes
        'CON', 'PRN', 'AUX', 'NUL',  # Windows reserved names
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]

    def __init__(self):
        self.magic = None
        self._init_magic()

    def _init_magic(self):
        """Initialize python-magic if available"""
        try:
            import magic
            self.magic = magic.Magic(mime=True)
            logger.info("python-magic initialized for MIME detection")
        except ImportError:
            logger.warning("python-magic not available - MIME validation disabled")
        except Exception as e:
            logger.warning(f"python-magic initialization failed: {e}")

    def validate_file(self, file: UploadFile) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Comprehensive file validation

        Returns:
            (is_valid, error_message, safe_filename)
        """
        try:
            # Get filename
            filename = file.filename
            if not filename:
                return False, "No filename provided", None

            # Reject path separators, control characters, and Windows device names.
            if self._has_dangerous_patterns(filename) or os.path.basename(filename) != filename or any(ord(c) < 32 for c in filename):
                return False, "Filename is not allowed", None
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in self.ALLOWED_EXTENSIONS:
                return False, f"File type '{file_ext}' not allowed", None

            # Get file size
            file_size = 0
            file.file.seek(0, 2)  # Seek to end of the spooled upload
            file_size = file.file.tell()
            file.file.seek(0)  # Seek back to beginning

            if file_size > self.MAX_FILE_SIZE:
                return False, f"File size {file_size} exceeds maximum {self.MAX_FILE_SIZE}", None

            if file_size == 0:
                return False, "File is empty", None

            # Validate content signatures even when libmagic is unavailable.
            content = file.file.read(4096)
            file.file.seek(0)
            detected_mime = self._detect_signature(content, file_ext)
            if detected_mime is None:
                return False, "File content does not match its extension", None
            if self.magic:
                try:
                    magic_mime = self.magic.from_buffer(content)
                    if magic_mime not in self.ALLOWED_MIME_TYPES and not (magic_mime == "application/zip" and file_ext in {".docx", ".xlsx", ".pptx"}):
                        return False, "File content type is not supported", None
                    detected_mime = self._detect_signature(content, file_ext) if magic_mime == "application/zip" else magic_mime
                except Exception as exc:
                    logger.warning("MIME validation failed: %s", exc)
            expected_ext = self.ALLOWED_MIME_TYPES.get(detected_mime)
            if expected_ext and file_ext != expected_ext:
                return False, "File extension does not match its content type", None

            # Generate safe filename
            safe_filename = self._generate_safe_filename(filename)

            return True, None, safe_filename

        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False, f"File validation failed: {str(e)}", None

    def _detect_signature(self, content: bytes, extension: str) -> Optional[str]:
        signatures = {
            b"%PDF-": "application/pdf",
            b"PK\\x03\\x04": "application/zip",
            b"GIF8": "image/gif",
            b"\\x89PNG\\r\\n\\x1a\\n": "image/png",
            b"\\xff\\xd8\\xff": "image/jpeg",
            b"RIFF": "image/webp",
        }
        for marker, mime in signatures.items():
            if content.startswith(marker):
                if extension in {".docx", ".xlsx", ".pptx"}:
                    return {".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}[extension]
                return mime
        if extension in {".txt", ".md", ".csv"}:
            try:
                content.decode("utf-8")
                return {".txt": "text/plain", ".md": "text/markdown", ".csv": "text/csv"}[extension]
            except UnicodeDecodeError:
                return None
        return None
    def _has_dangerous_patterns(self, filename: str) -> bool:
        """Check for dangerous filename patterns"""
        filename_upper = filename.upper()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.upper() in filename_upper:
                return True
        return False

    def _generate_safe_filename(self, filename: str) -> str:
        """Generate a safe filename"""
        # Remove dangerous characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
        safe_filename = "".join(c for c in filename if c in safe_chars)

        # Ensure filename starts with alphanumeric
        if safe_filename and not safe_filename[0].isalnum():
            safe_filename = "file_" + safe_filename

        # Ensure filename is not empty
        if not safe_filename:
            safe_filename = "upload_" + hashlib.md5(filename.encode()).hexdigest()[:8]

        # Get extension
        _, ext = os.path.splitext(filename)
        if ext and not safe_filename.endswith(ext):
            safe_filename += ext

        return safe_filename

    def calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()


class MalwareScanner:
    """
    Malware scanning interface for file uploads
    Supports ClamAV or local scanning when available
    """

    def __init__(self):
        self.clamav_available = False
        self._check_clamav()

    def _check_clamav(self):
        """Check if ClamAV is available"""
        try:
            import pyclamd
            self.clamd = pyclamd.ClamdUnixSocket()
            self.clamav_available = True
            logger.info("ClamAV scanner initialized")
        except ImportError:
            logger.warning("pyclamd not available - malware scanning disabled")
        except Exception as e:
            logger.warning(f"ClamAV initialization failed: {e}")

    def scan_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Scan file for malware

        Returns:
            (is_clean, error_message)
        """
        if not self.clamav_available:
            return True, "Malware scanning not available"

        try:
            result = self.clamd.scan_file(file_path)

            if result is None:
                return True, None

            # ClamAV returns {file_path: ('FOUND', 'virus_name')} or {file_path: ('OK', None)}
            for filepath, status in result.items():
                if status[0] == 'FOUND':
                    virus_name = status[1] if len(status) > 1 else 'unknown'
                    logger.warning(f"Malware detected in {filepath}: {virus_name}")
                    return False, f"Malware detected: {virus_name}"

            return True, None

        except Exception as e:
            logger.error(f"Malware scan failed: {e}")
            return True, f"Malware scan failed: {str(e)}"  # Don't block on scan failure


def validate_upload(file: UploadFile) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Convenience function to validate file upload

    Returns:
        (is_valid, error_message, safe_filename)
    """
    validator = FileSecurityValidator()
    return validator.validate_file(file)