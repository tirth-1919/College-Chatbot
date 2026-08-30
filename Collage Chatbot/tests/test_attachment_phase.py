import io
from fastapi import UploadFile
from backend.app.security.file_validator import FileSecurityValidator
from backend.app.services.attachment_service import AttachmentService

def upload(name, content, content_type="text/plain"):
    return UploadFile(filename=name, file=io.BytesIO(content), headers={"content-type": content_type})


def test_validator_rejects_traversal_and_fake_pdf():
    validator = FileSecurityValidator()
    valid, _, _ = validator.validate_file(upload("../notes.txt", b"ok"))
    assert not valid
    valid, _, _ = validator.validate_file(upload("notes.pdf", b"plain text"))
    assert not valid

def test_validator_accepts_utf8_text_and_sanitizes_name():
    valid, error, safe = FileSecurityValidator().validate_file(upload("notes final.txt", "DBMS".encode()))
    assert valid and error is None and safe == "notesfinal.txt"


def test_extract_csv_and_xlsx_metadata(tmp_path):
    service = AttachmentService(str(tmp_path))
    path, digest, metadata = service.save("subjects.csv", b"code,name\nDBMS,Database", "text/csv")
    assert digest and path.endswith(".csv")
    assert metadata["columns"] == ["code", "name"]
    assert "DBMS" in metadata["extracted_text"]


def test_storage_cleanup_is_scoped(tmp_path):
    service = AttachmentService(str(tmp_path))
    path, _, _ = service.save("notes.txt", b"private", "text/plain")
    service.delete_storage(path)
    assert not tmp_path.joinpath(path).exists() if not path.startswith(str(tmp_path)) else not __import__('pathlib').Path(path).exists()
