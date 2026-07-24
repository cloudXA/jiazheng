from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, text

from app.api.dependencies import CurrentUser, SessionDependency, SettingsDependency
from app.models import RiskCase, User
from app.schemas import (
    ApiResponse,
    LoginRequest,
    LoginResult,
    RiskAnalysis,
    RiskAnalyzeRequest,
    RiskCaseRead,
    RiskCaseStatus,
    RiskCaseStatusUpdate,
    RiskField,
    TranscriptionResult,
    UserInfo,
)
from app.security import create_access_token
from app.services.risk_workflow import get_risk_workflow
from app.services.tencent_asr import (
    MAX_RAW_AUDIO_BYTES,
    InvalidAudioError,
    TencentAsrError,
    TencentAsrService,
)
from app.services.wechat import WechatClient

router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
async def health() -> ApiResponse[dict[str, str]]:
    return ApiResponse(data={"status": "ok"})


@router.get("/health/ready", response_model=ApiResponse[dict[str, str]])
async def readiness(session: SessionDependency) -> ApiResponse[dict[str, str]]:
    await session.execute(text("SELECT 1"))
    return ApiResponse(data={"status": "ready"})


@router.post("/api/auth/login", response_model=ApiResponse[LoginResult])
async def login(
    payload: LoginRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> ApiResponse[LoginResult]:
    try:
        identity = await WechatClient(settings).resolve_identity(payload.code, payload.phone_code)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from None

    result = await session.execute(select(User).where(User.openid == identity.openid))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            openid=identity.openid,
            phone=identity.phone,
            nickname=payload.nick_name or "微信用户",
            avatar_url=payload.avatar_url or "",
        )
        session.add(user)
    else:
        user.phone = identity.phone or user.phone
        if payload.nick_name:
            user.nickname = payload.nick_name
        if payload.avatar_url:
            user.avatar_url = payload.avatar_url

    await session.commit()
    await session.refresh(user)
    token = create_access_token(user.id, settings)
    return ApiResponse(
        data=LoginResult(
            token=token,
            user_info=_user_info(user),
        )
    )


@router.post("/api/auth/logout", response_model=ApiResponse[None])
async def logout(_user: CurrentUser) -> ApiResponse[None]:
    return ApiResponse(data=None)


@router.get("/api/user/info", response_model=ApiResponse[UserInfo])
async def user_info(user: CurrentUser) -> ApiResponse[UserInfo]:
    return ApiResponse(data=_user_info(user))


@router.post("/api/risk/analyze", response_model=ApiResponse[RiskAnalysis])
async def analyze_risk(
    payload: RiskAnalyzeRequest,
    _user: CurrentUser,
) -> ApiResponse[RiskAnalysis]:
    analysis = await get_risk_workflow().analyze(payload.source_text)
    return ApiResponse(data=analysis)


@router.post("/api/cases", response_model=ApiResponse[RiskCaseRead])
async def create_case(
    payload: RiskAnalysis,
    user: CurrentUser,
    session: SessionDependency,
) -> ApiResponse[RiskCaseRead]:
    existing = await session.get(RiskCase, payload.id)
    if existing is not None:
        if existing.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="记录编号冲突")
        return ApiResponse(data=_case_read(existing))

    record = RiskCase(
        id=payload.id,
        user_id=user.id,
        source_text=payload.source_text,
        title=payload.title,
        risk_level=payload.risk_level.value,
        risk_label=payload.risk_label,
        summary=payload.summary,
        field_items=[
            item.model_dump(mode="json", by_alias=True) for item in payload.fields
        ],
        reasons=payload.reasons,
        missing_evidence=payload.missing_evidence,
        before_dispatch=payload.before_dispatch,
        confirmation_message=payload.confirmation_message,
        internal_note=payload.internal_note,
        refusal_action=payload.refusal_action,
        status=RiskCaseStatus.PENDING.value,
        version=1,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return ApiResponse(data=_case_read(record))


@router.get("/api/cases", response_model=ApiResponse[list[RiskCaseRead]])
async def list_cases(
    user: CurrentUser,
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ApiResponse[list[RiskCaseRead]]:
    result = await session.execute(
        select(RiskCase)
        .where(RiskCase.user_id == user.id)
        .order_by(RiskCase.created_at.desc())
        .limit(limit)
    )
    return ApiResponse(data=[_case_read(record) for record in result.scalars()])


@router.get("/api/cases/{case_id}", response_model=ApiResponse[RiskCaseRead])
async def get_case(
    case_id: str,
    user: CurrentUser,
    session: SessionDependency,
) -> ApiResponse[RiskCaseRead]:
    record = await _owned_case(case_id, user, session)
    return ApiResponse(data=_case_read(record))


@router.patch("/api/cases/{case_id}/status", response_model=ApiResponse[RiskCaseRead])
async def update_case_status(
    case_id: str,
    payload: RiskCaseStatusUpdate,
    user: CurrentUser,
    session: SessionDependency,
) -> ApiResponse[RiskCaseRead]:
    record = await _owned_case(case_id, user, session, lock=True)
    if payload.version is not None and payload.version != record.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="记录已被其他操作更新，请刷新后重试",
        )

    record.status = payload.status.value
    record.version += 1
    await session.commit()
    await session.refresh(record)
    return ApiResponse(data=_case_read(record))


@router.post("/api/ai/transcribe", response_model=ApiResponse[TranscriptionResult])
async def transcribe_audio(
    _user: CurrentUser,
    settings: SettingsDependency,
    audio: Annotated[UploadFile, File()],
) -> ApiResponse[TranscriptionResult]:
    provider = settings.asr_provider.lower()
    if provider == "mock":
        return ApiResponse(
            data=TranscriptionResult(
                simulated=True,
                text=(
                    "客户李女士需要住家照护，先试工7天。阿姨由合作方推荐，"
                    "服务成功后收取首月工资30%的服务费。客户电话里同意过，"
                    "但还没有微信书面确认，也没有说明退款和不得绕开公司私签的规则。"
                ),
            )
        )

    if provider == "tencent":
        if not settings.tencent_asr_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="腾讯云语音识别尚未配置，请先设置 SecretId 和 SecretKey",
            )
        audio_bytes = await audio.read(MAX_RAW_AUDIO_BYTES + 1)
        try:
            text_result = await TencentAsrService(settings).transcribe(
                audio_bytes,
                filename=audio.filename,
                content_type=audio.content_type,
            )
        except InvalidAudioError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from None
        except TencentAsrError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(error),
            ) from None
        return ApiResponse(
            data=TranscriptionResult(
                simulated=False,
                text=text_result,
            )
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"不支持的语音服务：{settings.asr_provider}",
    )


async def _owned_case(
    case_id: str,
    user: User,
    session: SessionDependency,
    *,
    lock: bool = False,
) -> RiskCase:
    statement = select(RiskCase).where(
        RiskCase.id == case_id,
        RiskCase.user_id == user.id,
    )
    if lock:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    return record


def _user_info(user: User) -> UserInfo:
    return UserInfo(
        avatar_url=user.avatar_url,
        nick_name=user.nickname,
        phone=user.phone or "",
    )


def _case_read(record: RiskCase) -> RiskCaseRead:
    created_at = record.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return RiskCaseRead(
        id=record.id,
        created_at=int(created_at.timestamp() * 1000),
        source_text=record.source_text,
        title=record.title,
        risk_level=record.risk_level,
        risk_label=record.risk_label,
        summary=record.summary,
        fields=[RiskField.model_validate(item) for item in record.field_items],
        reasons=record.reasons,
        missing_evidence=record.missing_evidence,
        before_dispatch=record.before_dispatch,
        confirmation_message=record.confirmation_message,
        internal_note=record.internal_note,
        refusal_action=record.refusal_action,
        status=record.status,
        version=record.version,
    )
