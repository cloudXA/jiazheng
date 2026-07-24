import asyncio
import base64
import json
import logging
from pathlib import Path

from tencentcloud.asr.v20190614 import asr_client, models
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

from app.config import Settings

logger = logging.getLogger(__name__)

MAX_BASE64_AUDIO_BYTES = 3 * 1024 * 1024
MAX_RAW_AUDIO_BYTES = (MAX_BASE64_AUDIO_BYTES // 4) * 3

SUPPORTED_FORMATS = {
    "aac",
    "amr",
    "m4a",
    "mp3",
    "ogg-opus",
    "pcm",
    "silk",
    "speex",
    "wav",
}
CONTENT_TYPE_FORMATS = {
    "audio/aac": "aac",
    "audio/amr": "amr",
    "audio/m4a": "m4a",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/ogg": "ogg-opus",
    "audio/wav": "wav",
    "audio/x-m4a": "m4a",
    "audio/x-wav": "wav",
}


class InvalidAudioError(ValueError):
    """Raised when an uploaded audio file cannot be sent to Tencent ASR."""


class TencentAsrError(RuntimeError):
    """Raised when Tencent ASR cannot return a usable transcription."""


class TencentAsrService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str | None,
        content_type: str | None,
    ) -> str:
        voice_format = self._validate_audio(
            audio_bytes,
            filename=filename,
            content_type=content_type,
        )
        return await asyncio.to_thread(
            self._recognize_sync,
            audio_bytes,
            voice_format,
        )

    def _recognize_sync(self, audio_bytes: bytes, voice_format: str) -> str:
        credentials = credential.Credential(
            self._settings.tencent_secret_id,
            self._settings.tencent_secret_key,
        )
        http_profile = HttpProfile()
        http_profile.endpoint = "asr.tencentcloudapi.com"
        http_profile.reqTimeout = self._settings.tencent_asr_timeout_seconds
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = asr_client.AsrClient(
            credentials,
            self._settings.tencent_asr_region,
            client_profile,
        )

        payload: dict[str, object] = {
            "EngSerViceType": self._settings.tencent_asr_engine,
            "ProjectId": 0,
            "SubServiceType": 2,
            "SourceType": 1,
            "VoiceFormat": voice_format,
            "Data": base64.b64encode(audio_bytes).decode("ascii"),
            "DataLen": len(audio_bytes),
            "FilterPunc": 0,
            "ConvertNumMode": 1,
        }
        if self._settings.tencent_asr_hotword_list:
            payload["HotwordList"] = self._settings.tencent_asr_hotword_list

        request = models.SentenceRecognitionRequest()
        request.from_json_string(json.dumps(payload, ensure_ascii=True))
        logger.info(
            "Submitting audio to Tencent ASR. bytes=%d format=%s engine=%s",
            len(audio_bytes),
            voice_format,
            self._settings.tencent_asr_engine,
        )
        try:
            response = client.SentenceRecognition(request)
        except TencentCloudSDKException as error:
            error_code = error.get_code() or "UnknownError"
            logger.warning(
                (
                    "Tencent ASR request failed. code=%s message=%s request_id=%s "
                    "bytes=%d format=%s engine=%s"
                ),
                error_code,
                error.get_message(),
                error.get_request_id(),
                len(audio_bytes),
                voice_format,
                self._settings.tencent_asr_engine,
            )
            if error_code == "FailedOperation.ErrorRecognize":
                raise TencentAsrError(
                    "腾讯云未识别到有效语音，请录制5秒以上并靠近麦克风重试"
                ) from None
            raise TencentAsrError(f"腾讯云语音识别失败（{error_code}）") from None

        result = (response.Result or "").strip()
        if not result:
            raise TencentAsrError("没有识别到清晰语音，请靠近麦克风后重试")
        return result

    @staticmethod
    def _validate_audio(
        audio_bytes: bytes,
        *,
        filename: str | None,
        content_type: str | None,
    ) -> str:
        if not audio_bytes:
            raise InvalidAudioError("录音文件为空，请重新录制")
        if len(base64.b64encode(audio_bytes)) > MAX_BASE64_AUDIO_BYTES:
            raise InvalidAudioError("录音文件过大，请将录音控制在60秒以内")

        extension = Path(filename or "").suffix.lower().lstrip(".")
        if extension in SUPPORTED_FORMATS:
            return extension

        normalized_content_type = (content_type or "").split(";", maxsplit=1)[0].lower()
        voice_format = CONTENT_TYPE_FORMATS.get(normalized_content_type)
        if voice_format:
            return voice_format
        raise InvalidAudioError("不支持该录音格式，请使用 MP3、M4A、AAC 或 WAV")
