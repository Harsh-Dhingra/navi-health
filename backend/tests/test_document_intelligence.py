from app.services.document_intelligence import (
    chunk_text,
    classify_document,
    extract_fields,
)


def test_classify_document_eob():
    assert classify_document("This is your Explanation of Benefits for the visit.") == "eob"


def test_classify_document_insurance_card():
    assert classify_document("Member ID: 12345\nAetna PPO") == "insurance_card"


def test_classify_document_unknown():
    assert classify_document("Just some random text with no signal.") == "unknown"


def test_extract_fields_member_and_group():
    text = "Member ID: W123456789\nGroup Number: GRP998\nAetna Choice POS"
    fields = extract_fields(text, "insurance_card")
    assert fields["member_id"] == "W123456789"
    assert fields["group_number"] == "GRP998"
    assert fields["payer_name"] == "Aetna"


def test_chunk_text_covers_full_input_with_overlap():
    text = "x" * 2500
    chunks = chunk_text(text, chunk_size=800, overlap=100)
    assert "".join(chunks) != ""
    assert len(chunks) >= 3
    # every character position is covered by at least one chunk
    covered = set()
    pos = 0
    for chunk in chunks:
        covered.update(range(pos, pos + len(chunk)))
        pos += 800 - 100
    assert len(covered) >= len(text) - 100


def test_chunk_text_empty_input():
    assert chunk_text("") == []
