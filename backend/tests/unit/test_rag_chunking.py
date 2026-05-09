from app.services.rag_service import chunk_text


def test_short_text_one_chunk():
    out = chunk_text("hello world")
    assert out == ["hello world"]


def test_long_text_overlap():
    text = "abcdefghij" * 200  # 2000 chars
    chunks = chunk_text(text, chunk_size=400, overlap=80)
    assert all(len(c) <= 400 for c in chunks)
    # overlap means consecutive chunks share content
    assert chunks[0][-80:] == chunks[1][:80]
