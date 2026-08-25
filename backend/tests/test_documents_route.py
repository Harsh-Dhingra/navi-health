from app.api.routes.documents import _safe_filename


def test_safe_filename_strips_path_traversal():
    assert _safe_filename("../../etc/passwd") == "passwd"
    assert _safe_filename("../../../secrets.env") == "secrets.env"


def test_safe_filename_strips_unsafe_characters():
    assert _safe_filename("my insurance card!!.pdf") == "my_insurance_card__.pdf"


def test_safe_filename_handles_empty_input():
    assert _safe_filename("") == "upload"
    assert _safe_filename(None) == "upload"
