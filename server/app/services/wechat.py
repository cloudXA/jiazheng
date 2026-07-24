from dataclasses import dataclass
from hashlib import sha256

import httpx

from app.config import Settings


@dataclass(frozen=True)
class WechatIdentity:
    openid: str
    phone: str


class WechatClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def resolve_identity(self, code: str, phone_code: str) -> WechatIdentity:
        if not self._settings.wechat_configured:
            if self._settings.app_env == "production":
                raise RuntimeError("WeChat credentials are not configured")
            digest = sha256(code.encode("utf-8")).hexdigest()[:24]
            return WechatIdentity(openid=f"dev-{digest}", phone="138****0001")

        async with httpx.AsyncClient(timeout=10) as client:
            session_response = await client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": self._settings.wechat_app_id,
                    "secret": self._settings.wechat_app_secret,
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
            session_response.raise_for_status()
            session_data = session_response.json()
            openid = session_data.get("openid")
            if not openid:
                raise RuntimeError("WeChat code exchange failed")

            token_response = await client.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": self._settings.wechat_app_id,
                    "secret": self._settings.wechat_app_secret,
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise RuntimeError("WeChat access token exchange failed")

            phone_response = await client.post(
                "https://api.weixin.qq.com/wxa/business/getuserphonenumber",
                params={"access_token": access_token},
                json={"code": phone_code},
            )
            phone_response.raise_for_status()
            phone_info = phone_response.json().get("phone_info") or {}
            phone = phone_info.get("purePhoneNumber") or ""
            return WechatIdentity(openid=openid, phone=phone)

