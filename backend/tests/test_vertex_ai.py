# backend/tests/test_vertex_ai.py
import pytest
from app.services.vertex_ai import FakeVertexClient, check_for_biometric_content
from app.models.scan import ParsedID


@pytest.mark.asyncio
async def test_fake_client_returns_parsed_id():
    client = FakeVertexClient()
    result = await client.extract_id_fields(b"fakeimagebytes")
    assert isinstance(result, ParsedID)


@pytest.mark.asyncio
async def test_fake_client_returns_configured_data():
    fixed = ParsedID(first_name="Jane", last_name="Doe", confidence=0.95)
    client = FakeVertexClient(response=fixed)
    result = await client.extract_id_fields(b"anyimage")
    assert result.first_name == "Jane"
    assert result.last_name == "Doe"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_fake_client_raises_on_injected_error():
    client = FakeVertexClient(raise_error=ValueError("Vertex AI unavailable"))
    with pytest.raises(ValueError, match="Vertex AI unavailable"):
        await client.extract_id_fields(b"anyimage")


def test_biometric_check_flags_eye_color():
    assert check_for_biometric_content('{"first_name":"John","notes":"blue eyes"}') is True


def test_biometric_check_flags_facial_description():
    assert check_for_biometric_content("the person has a broad nose and square jaw") is True


def test_biometric_check_passes_clean_json():
    clean = '{"first_name":"John","last_name":"Smith","doc_number":"AB123456"}'
    assert check_for_biometric_content(clean) is False


def test_biometric_check_passes_address_fields():
    assert check_for_biometric_content('{"city":"Chicago","state":"IL"}') is False
