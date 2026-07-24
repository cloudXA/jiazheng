import re
import time
from uuid import uuid4

from app.schemas import (
    ExtractedFacts,
    RiskAnalysis,
    RiskField,
    RiskFieldStatus,
    RiskLevel,
)

NEGATIVE_MARKERS = (
    "没有",
    "还没",
    "尚未",
    "未书面",
    "没书面",
    "未确认",
    "没确认",
    "未说明",
    "没说明",
    "没说清",
    "不清楚",
)

SERVICE_TYPES = ("老人照护", "育儿服务", "钟点服务", "保洁服务", "住家服务")


def includes_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def has_positive_mention(text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        index = text.find(keyword)
        if index < 0:
            continue
        context = text[max(0, index - 10) : index + len(keyword) + 14]
        if not includes_any(context, NEGATIVE_MARKERS):
            return True
    return False


def has_negative_mention(text: str, keywords: tuple[str, ...]) -> bool:
    for keyword in keywords:
        index = text.find(keyword)
        if index < 0:
            continue
        context = text[max(0, index - 10) : index + len(keyword) + 14]
        if includes_any(context, NEGATIVE_MARKERS):
            return True
    return False


def pick_service_type(text: str) -> str | None:
    if includes_any(text, ("老人", "照护", "护理", "陪护")):
        return "老人照护"
    if includes_any(text, ("育儿", "育婴", "月嫂")):
        return "育儿服务"
    if includes_any(text, ("钟点", "小时工")):
        return "钟点服务"
    if includes_any(text, ("保洁", "清洁")):
        return "保洁服务"
    if includes_any(text, ("住家", "保姆")):
        return "住家服务"
    return None


def normalize_service_type(value: str | None) -> str | None:
    if not value:
        return None
    for service_type in SERVICE_TYPES:
        if service_type in value or value in service_type:
            return service_type
    return None


def extract_heuristic_facts(source_text: str) -> ExtractedFacts:
    text = source_text.strip()
    trial_match = re.search(r"(?:试工|试用)\s*(\d+)\s*天", text)
    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    fixed_fee_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:元|块)", text)
    customer_match = re.search(
        r"客户(?:叫|姓名是|是)?\s*([\u4e00-\u9fa5]{1,4}(?:女士|先生))",
        text,
    )

    worker_source: str | None = None
    if "第三方" in text:
        worker_source = "第三方阿姨"
    elif "合作" in text:
        worker_source = "合作阿姨"
    elif includes_any(text, ("公司员工", "公司阿姨")):
        worker_source = "公司阿姨"

    charge_method: str | None = None
    charge_value: str | None = None
    if percent_match:
        charge_method = "按首月工资比例"
        charge_value = f"{percent_match.group(1)}%"
    elif includes_any(text, ("年费", "包年")):
        charge_method = "年费"
    elif fixed_fee_match:
        charge_method = "固定金额"
        charge_value = f"{fixed_fee_match.group(1)}元"

    return ExtractedFacts(
        customer_name=customer_match.group(1) if customer_match else None,
        service_type=pick_service_type(text),
        trial_days=int(trial_match.group(1)) if trial_match else None,
        worker_source=worker_source,
        charge_method=charge_method,
        charge_value=charge_value,
        written_confirmed=has_positive_mention(
            text,
            ("微信确认", "书面确认", "签字", "已签合同", "回复确认"),
        ),
        decision_maker_confirmed=has_positive_mention(
            text,
            ("决策人", "本人决定", "家属同意", "子女同意"),
        ),
        no_bypass_confirmed=has_positive_mention(
            text,
            ("不得绕开", "不能绕开", "不私签", "不得私签", "禁止私签"),
        ),
        refund_explained=has_positive_mention(
            text,
            ("退款规则", "退费规则", "退款约定", "退费约定"),
        ),
        care_safety_confirmed=all(
            keyword in text for keyword in ("病史", "禁忌", "应急联系人")
        ),
        has_fee_dispute=includes_any(
            text,
            ("反悔", "不认", "不承认", "不收费", "不要收费", "拒绝付费"),
        ),
        has_safety_event=includes_any(
            text,
            ("噎", "受伤", "摔倒", "事故", "急救"),
        ),
    )


def apply_guardrails(source_text: str, model_facts: ExtractedFacts) -> ExtractedFacts:
    heuristic = extract_heuristic_facts(source_text)

    written_confirmed = model_facts.written_confirmed or heuristic.written_confirmed
    if has_negative_mention(
        source_text,
        ("微信确认", "书面确认", "签字", "合同", "回复确认"),
    ):
        written_confirmed = False

    decision_maker_confirmed = (
        model_facts.decision_maker_confirmed or heuristic.decision_maker_confirmed
    )
    if has_negative_mention(source_text, ("决策人", "家属确认", "子女确认")):
        decision_maker_confirmed = False

    no_bypass_confirmed = model_facts.no_bypass_confirmed or heuristic.no_bypass_confirmed
    if has_negative_mention(
        source_text,
        ("不得绕开", "不能绕开", "不私签", "不得私签", "禁止私签"),
    ):
        no_bypass_confirmed = False

    refund_explained = model_facts.refund_explained or heuristic.refund_explained
    if has_negative_mention(
        source_text,
        ("退款规则", "退费规则", "退款约定", "退费约定"),
    ):
        refund_explained = False

    return ExtractedFacts(
        customer_name=model_facts.customer_name or heuristic.customer_name,
        service_type=normalize_service_type(model_facts.service_type)
        or heuristic.service_type,
        trial_days=model_facts.trial_days
        if model_facts.trial_days is not None
        else heuristic.trial_days,
        worker_source=model_facts.worker_source or heuristic.worker_source,
        charge_method=model_facts.charge_method or heuristic.charge_method,
        charge_value=model_facts.charge_value or heuristic.charge_value,
        written_confirmed=written_confirmed,
        decision_maker_confirmed=decision_maker_confirmed,
        no_bypass_confirmed=no_bypass_confirmed,
        refund_explained=refund_explained,
        care_safety_confirmed=(
            model_facts.care_safety_confirmed or heuristic.care_safety_confirmed
        ),
        has_fee_dispute=model_facts.has_fee_dispute or heuristic.has_fee_dispute,
        has_safety_event=model_facts.has_safety_event or heuristic.has_safety_event,
    )


def build_risk_analysis(
    source_text: str,
    facts: ExtractedFacts,
    extraction_source: str,
) -> RiskAnalysis:
    customer_name = facts.customer_name or "未记录"
    service_type = facts.service_type or "待补充"
    worker_source = facts.worker_source or "待补充"
    charge_method = facts.charge_method or "待补充"
    charge_value = facts.charge_value or "待补充"
    trial_value = f"{facts.trial_days}天" if facts.trial_days is not None else "未说明"
    is_care_service = service_type in {"老人照护", "育儿服务"}

    missing_evidence: list[str] = []
    if customer_name == "未记录":
        missing_evidence.append("客户姓名或脱敏代号")
    if service_type == "待补充":
        missing_evidence.append("具体服务类型与服务范围")
    if worker_source == "待补充":
        missing_evidence.append("阿姨来源及合作关系")
    if charge_value == "待补充":
        missing_evidence.append("收费方式与具体金额或比例")
    if not facts.written_confirmed:
        missing_evidence.append("客户对收费规则的书面确认")
    if not facts.decision_maker_confirmed:
        missing_evidence.append("家庭实际决策人的确认")
    if not facts.no_bypass_confirmed:
        missing_evidence.append("不得绕开公司私签的书面约定")
    if not facts.refund_explained:
        missing_evidence.append("试工结束、换人及退款规则")
    if is_care_service and not facts.care_safety_confirmed:
        missing_evidence.append("照护对象病史、禁忌及应急联系人")

    reasons: list[str] = []
    if facts.has_fee_dispute:
        reasons.append("客户已出现收费反悔或拒绝确认信号，口头承诺难以单独支撑后续追偿。")
    if worker_source == "第三方阿姨":
        reasons.append("阿姨来自第三方，服务责任、人员关系和保险边界需要另行明确。")
    if not facts.written_confirmed:
        reasons.append("收费目前缺少微信或合同书面确认，容易产生介绍成功后不认服务费的争议。")
    if not facts.no_bypass_confirmed:
        reasons.append("尚未确认防私签条款，试工后客户与阿姨绕开公司的风险较高。")
    if is_care_service and (facts.has_safety_event or not facts.care_safety_confirmed):
        reasons.append("照护服务涉及人身安全，健康信息和紧急处置责任尚未形成完整记录。")
    if not reasons:
        reasons.append("关键信息较完整，仍应在派单前让客户以文字回复确认。")

    high_risk = (
        facts.has_fee_dispute
        or facts.has_safety_event
        or worker_source == "第三方阿姨"
        or includes_any(source_text, ("绕开公司", "私下签约"))
    )
    risk_level = (
        RiskLevel.HIGH
        if high_risk
        else RiskLevel.MEDIUM
        if len(missing_evidence) >= 3
        else RiskLevel.LOW
    )
    risk_label = {
        RiskLevel.HIGH: "高风险",
        RiskLevel.MEDIUM: "中风险",
        RiskLevel.LOW: "低风险",
    }[risk_level]

    before_dispatch = [
        "确认客户本人或家庭实际决策人，并留存微信回复。",
        f"确认服务类型、试工期限和阿姨来源：{service_type} / {trial_value} / {worker_source}。",
        f"确认服务费标准：{charge_method}，{charge_value}。",
        "明确不得绕开公司与阿姨私签、私下结算。",
        "发送换人、终止和退款规则，并让客户回复“确认无误”。",
    ]
    if is_care_service:
        before_dispatch.append("收集照护对象病史、饮食禁忌、吞咽/行动风险和紧急联系人。")

    confirmation_message = "\n".join(
        [
            f"您好，为避免后续理解不一致，现将本次"
            f"{'家政服务' if service_type == '待补充' else service_type}合作要点确认如下：",
            f"1. 客户称呼：{customer_name}；试工安排：{trial_value}。",
            f"2. 阿姨来源：{worker_source}。",
            f"3. 服务成功后的服务费：{charge_method}，标准为{charge_value}。",
            "4. 未经公司书面同意，客户与阿姨不绕开公司私下签约或结算。",
            "5. 换人、终止及退款按双方书面确认的规则执行。",
            "请核对后回复“以上确认无误”。收到确认后，我们再安排派单。",
        ]
    )

    fields = [
        RiskField(
            key="customer",
            label="客户",
            value=customer_name,
            status=RiskFieldStatus.MISSING
            if customer_name == "未记录"
            else RiskFieldStatus.INFO,
        ),
        RiskField(
            key="service",
            label="服务类型",
            value=service_type,
            status=RiskFieldStatus.MISSING
            if service_type == "待补充"
            else RiskFieldStatus.INFO,
        ),
        RiskField(
            key="trial",
            label="试工",
            value=trial_value,
            status=RiskFieldStatus.INFO
            if facts.trial_days is not None
            else RiskFieldStatus.MISSING,
        ),
        RiskField(
            key="worker",
            label="阿姨来源",
            value=worker_source,
            status=RiskFieldStatus.MISSING
            if worker_source == "待补充"
            else RiskFieldStatus.INFO,
        ),
        RiskField(
            key="fee",
            label="收费",
            value=f"{charge_method} · {charge_value}",
            status=RiskFieldStatus.MISSING
            if charge_value == "待补充"
            else RiskFieldStatus.INFO,
        ),
        _confirmation_field("written", "书面确认", facts.written_confirmed),
        _confirmation_field("decision", "决策人", facts.decision_maker_confirmed),
        _confirmation_field("bypass", "防私签", facts.no_bypass_confirmed),
        _confirmation_field(
            "refund",
            "退款规则",
            facts.refund_explained,
            confirmed_value="已说明",
            missing_value="未说明",
        ),
    ]

    return RiskAnalysis(
        id=f"case-{uuid4().hex}",
        created_at=int(time.time() * 1000),
        source_text=source_text.strip(),
        title=f"{customer_name if customer_name != '未记录' else '待补客户'} · {service_type}",
        risk_level=risk_level,
        risk_label=risk_label,
        summary={
            RiskLevel.HIGH: "先暂停派单，补齐收费、责任和人员关系证据。",
            RiskLevel.MEDIUM: "信息尚不完整，完成书面确认后再派单。",
            RiskLevel.LOW: "核心信息基本完整，发送确认话术留证后可推进。",
        }[risk_level],
        fields=fields,
        reasons=reasons[:4],
        missing_evidence=missing_evidence,
        before_dispatch=before_dispatch,
        confirmation_message=confirmation_message,
        internal_note=(
            f"原始沟通已留存。当前{risk_label}，缺失项{len(missing_evidence)}个。"
            f"提取方式：{extraction_source}。派单前由业务人员复核，AI结果不替代合同审核。"
        ),
        refusal_action=(
            "客户拒绝书面确认时暂停派单，不继续垫付人员与协调成本；"
            "由负责人再次说明收费和责任边界。"
        ),
    )


def _confirmation_field(
    key: str,
    label: str,
    confirmed: bool,
    *,
    confirmed_value: str = "已确认",
    missing_value: str = "未确认",
) -> RiskField:
    return RiskField(
        key=key,
        label=label,
        value=confirmed_value if confirmed else missing_value,
        status=RiskFieldStatus.CONFIRMED if confirmed else RiskFieldStatus.MISSING,
    )
