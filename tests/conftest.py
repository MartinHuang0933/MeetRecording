import os
import pytest

os.environ.setdefault("LINE_CHANNEL_SECRET", "test_secret")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")


@pytest.fixture
def sample_audio_bytes():
    """Minimal valid audio bytes for testing."""
    return b"\x00" * 1024


@pytest.fixture
def tmp_audio_file(tmp_path, sample_audio_bytes):
    """Create a temporary audio file."""
    audio_file = tmp_path / "test.m4a"
    audio_file.write_bytes(sample_audio_bytes)
    return str(audio_file)
