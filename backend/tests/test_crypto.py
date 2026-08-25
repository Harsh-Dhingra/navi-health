from app.core.crypto import EncryptedJSON, EncryptedString


def test_encrypted_string_roundtrip():
    field = EncryptedString(500)
    ciphertext = field.process_bind_param("member-12345", None)

    assert ciphertext != "member-12345"
    assert field.process_result_value(ciphertext, None) == "member-12345"


def test_encrypted_string_none_passthrough():
    field = EncryptedString(500)
    assert field.process_bind_param(None, None) is None
    assert field.process_result_value(None, None) is None


def test_encrypted_json_roundtrip():
    field = EncryptedJSON()
    payload = {"member_id": "abc123", "nested": {"x": 1}}
    ciphertext = field.process_bind_param(payload, None)

    assert isinstance(ciphertext, str)
    assert field.process_result_value(ciphertext, None) == payload
