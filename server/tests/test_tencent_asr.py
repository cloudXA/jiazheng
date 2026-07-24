import pytest

from app.config import Settings
from app.services.tencent_asr import (
    MAX_RAW_AUDIO_BYTES,
    InvalidAudioError,
    TencentAsrService,
)


def tencent_settings() -> Settings:
    return Settings(
        asr_provider="tencent",
        tencent_secret_id="test-secret-id",
        tencent_secret_key="test-secret-key",
    )


@pytest.mark.asyncio
async def test_transcribe_uses_mp3_format(monkeypatch: pytest.MonkeyPatch) -> None:
    service = TencentAsrService(tencent_settings())
    captured: dict[str, object] = {}

    def fake_recognize(audio_bytes: bytes, voice_format: str) -> str:
        captured["audio_bytes"] = audio_bytes
        captured["voice_format"] = voice_format
        return "客户需要一名住家保姆。"

    monkeypatch.setattr(service, "_recognize_sync", fake_recognize)

    result = await service.transcribe(
        b"example-audio",
        filename="voice.mp3",
        content_type="audio/mpeg",
    )

    assert result == "客户需要一名住家保姆。"
    assert captured == {
        "audio_bytes": b"example-audio",
        "voice_format": "mp3",
    }


@pytest.mark.asyncio
async def test_transcribe_uses_wav_format(monkeypatch: pytest.MonkeyPatch) -> None:
    service = TencentAsrService(tencent_settings())
    captured: dict[str, object] = {}

    def fake_recognize(audio_bytes: bytes, voice_format: str) -> str:
        captured["audio_bytes"] = audio_bytes
        captured["voice_format"] = voice_format
        return "客户需要一名住家保姆。"

    monkeypatch.setattr(service, "_recognize_sync", fake_recognize)

    result = await service.transcribe(
        b"example-wav-audio",
        filename="voice.wav",
        content_type="audio/wav",
    )

    assert result == "客户需要一名住家保姆。"
    assert captured == {
        "audio_bytes": b"example-wav-audio",
        "voice_format": "wav",
    }


@pytest.mark.asyncio
async def test_transcribe_rejects_empty_audio() -> None:
    service = TencentAsrService(tencent_settings())

    with pytest.raises(InvalidAudioError, match="录音文件为空"):
        await service.transcribe(
            b"",
            filename="voice.mp3",
            content_type="audio/mpeg",
        )


@pytest.mark.asyncio
async def test_transcribe_rejects_oversized_audio() -> None:
    service = TencentAsrService(tencent_settings())

    with pytest.raises(InvalidAudioError, match="录音文件过大"):
        await service.transcribe(
            b"x" * (MAX_RAW_AUDIO_BYTES + 1),
            filename="voice.mp3",
            content_type="audio/mpeg",
        )


@pytest.mark.asyncio
async def test_transcribe_rejects_unknown_format() -> None:
    service = TencentAsrService(tencent_settings())

    with pytest.raises(InvalidAudioError, match="不支持该录音格式"):
        await service.transcribe(
            b"example-audio",
            filename="voice.bin",
            content_type="application/octet-stream",
        )
