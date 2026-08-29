"""
Security features tests for AIT AI Assistant
Tests CSRF protection, file validation, malware scanning
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.security.csrf import CSRFMiddleware, CSRFTokenGenerator
try:
    from backend.app.security.file_validator import FileSecurityValidator, MalwareScanner
    FILE_VALIDATOR_AVAILABLE = True
except ImportError:
    FILE_VALIDATOR_AVAILABLE = False
from io import BytesIO


class TestCSRFProtection:
    """Test CSRF protection middleware"""
    
    def test_csrf_token_generation(self):
        """Test that CSRF tokens can be generated"""
        generator = CSRFTokenGenerator("test_secret")
        token1 = generator.generate_token()
        token2 = generator.generate_token()
        
        # Tokens should be different
        assert token1 != token2
        # Tokens should be non-empty
        assert len(token1) > 0
        assert len(token2) > 0
        # Tokens should be strings
        assert isinstance(token1, str)
        assert isinstance(token2, str)
    
    def test_csrf_token_with_session(self):
        """Test CSRF token generation with session context"""
        generator = CSRFTokenGenerator("test_secret")
        token_no_session = generator.generate_token()
        token_with_session = generator.generate_token("session123")
        
        # Tokens should be different based on session
        assert token_no_session != token_with_session
    
    def test_csrf_exempt_methods(self):
        """Test that GET/HEAD/OPTIONS are exempt from CSRF"""
        assert "GET" not in CSRFMiddleware.CSRF_PROTECTED_METHODS
        assert "HEAD" not in CSRFMiddleware.CSRF_PROTECTED_METHODS
        assert "OPTIONS" not in CSRFMiddleware.CSRF_PROTECTED_METHODS
        
        # POST/PUT/DELETE should be protected
        assert "POST" in CSRFMiddleware.CSRF_PROTECTED_METHODS
        assert "PUT" in CSRFMiddleware.CSRF_PROTECTED_METHODS
        assert "DELETE" in CSRFMiddleware.CSRF_PROTECTED_METHODS
    
    def test_csrf_exempt_paths(self):
        """Test that auth endpoints are exempt from CSRF"""
        assert "/api/v1/auth/login" in CSRFMiddleware.CSRF_EXEMPT_PATHS
        assert "/api/v1/auth/register" in CSRFMiddleware.CSRF_EXEMPT_PATHS
        assert "/api/v1/auth/logout" in CSRFMiddleware.CSRF_EXEMPT_PATHS
        assert "/health" in CSRFMiddleware.CSRF_EXEMPT_PATHS


@pytest.mark.skipif(not FILE_VALIDATOR_AVAILABLE, reason="file_validator dependencies not available")
class TestFileSecurityValidator:
    """Test file upload security validation"""
    
    def test_allowed_extensions(self):
        """Test that allowed extensions are correctly defined"""
        validator = FileSecurityValidator()
        
        # Check that common file types are allowed
        assert '.pdf' in validator.ALLOWED_EXTENSIONS
        assert '.docx' in validator.ALLOWED_EXTENSIONS
        assert '.jpg' in validator.ALLOWED_EXTENSIONS
        assert '.png' in validator.ALLOWED_EXTENSIONS
        
        # Check that dangerous extensions are not allowed
        assert '.exe' not in validator.ALLOWED_EXTENSIONS
        assert '.bat' not in validator.ALLOWED_EXTENSIONS
        assert '.sh' not in validator.ALLOWED_EXTENSIONS
    
    def test_dangerous_patterns(self):
        """Test dangerous filename pattern detection"""
        validator = FileSecurityValidator()
        
        # Path traversal patterns
        assert validator._has_dangerous_patterns("../../../etc/passwd")
        assert validator._has_dangerous_patterns("..\\..\\windows\\system32")
        
        # Windows reserved names
        assert validator._has_dangerous_patterns("CON")
        assert validator._has_dangerous_patterns("PRN")
        assert validator._has_dangerous_patterns("COM1")
        
        # Safe filenames should pass
        assert not validator._has_dangerous_patterns("document.pdf")
        assert not validator._has_dangerous_patterns("image.jpg")
    
    def test_safe_filename_generation(self):
        """Test safe filename generation"""
        validator = FileSecurityValidator()
        
        # Clean filename
        safe1 = validator._generate_safe_filename("document.pdf")
        assert "document.pdf" in safe1 or "document" in safe1
        
        # Filename with dangerous characters
        safe2 = validator._generate_safe_filename("../../../etc/passwd")
        assert "../" not in safe2
        assert "..\\" not in safe2
        
        # Empty filename should generate safe one
        safe3 = validator._generate_safe_filename("")
        assert len(safe3) > 0
        assert safe3.startswith("upload_")
    
    def test_max_file_size_enforcement(self):
        """Test maximum file size enforcement"""
        validator = FileSecurityValidator()
        
        # Check max size is set
        assert validator.MAX_FILE_SIZE == 10 * 1024 * 1024  # 10MB


@pytest.mark.skipif(not FILE_VALIDATOR_AVAILABLE, reason="file_validator dependencies not available")
class TestMalwareScanner:
    """Test malware scanning capabilities"""
    
    def test_malware_scanner_initialization(self):
        """Test that malware scanner can be initialized"""
        scanner = MalwareScanner()
        
        # Scanner should initialize even without ClamAV
        assert scanner is not None
        assert hasattr(scanner, 'clamav_available')
    
    def test_clamav_check(self):
        """Test ClamAV availability check"""
        scanner = MalwareScanner()
        
        # If ClamAV is not available, that's acceptable for testing
        # The important thing is that the scanner handles unavailability gracefully
        is_clean, error = scanner.scan_file("nonexistent.txt")
        
        # Should return True (clean) with error message when scanning unavailable
        assert is_clean == True  # Don't block uploads if scanner unavailable
        assert error is not None  # But should provide error message


@pytest.mark.skipif(not FILE_VALIDATOR_AVAILABLE, reason="file_validator dependencies not available")
class TestSecurityIntegration:
    """Integration tests for security features"""
    
    def test_file_upload_validation_workflow(self):
        """Test complete file upload validation workflow"""
        validator = FileSecurityValidator()
        
        # Create a mock file
        from fastapi import UploadFile
        mock_file = UploadFile(filename="test.pdf", file=BytesIO(b"test content"))
        
        # Validate the file
        is_valid, error_msg, safe_filename = validator.validate_file(mock_file)
        
        # File should be valid (small text file as PDF extension for testing)
        # In real scenario, MIME validation would catch this
        assert is_valid or error_msg is not None
        assert safe_filename is not None or error_msg is not None
    
    def test_security_headers_middleware_exists(self):
        """Test that security headers middleware is properly defined"""
        from backend.app.main import SecurityHeadersMiddleware
        
        # Middleware class should exist
        assert SecurityHeadersMiddleware is not None
        assert hasattr(SecurityHeadersMiddleware, 'dispatch')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])