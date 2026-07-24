from app.schemas import ExtractedFacts, RiskLevel
from app.services.rule_engine import apply_guardrails, build_risk_analysis


def test_negative_confirmation_cannot_be_upgraded_by_model() -> None:
    source_text = (
        "客户王女士需要住家保姆，阿姨由家政公司推荐，"
        "试工七天后签合同。电话里说了服务费30%，但没有微信或书面确认，"
        "客户现在不承认收费。"
    )
    optimistic_model_result = ExtractedFacts(
        customer_name="王女士",
        service_type="住家保姆",
        worker_source="公司推荐",
        trial_days=7,
        charge_method="服务费30%",
        written_confirmed=True,
        decision_maker_confirmed=True,
        refund_explained=True,
        has_safety_event=False,
        has_fee_dispute=False,
    )

    guarded = apply_guardrails(source_text, optimistic_model_result)
    analysis = build_risk_analysis(source_text, guarded, "deepseek+guardrails")

    assert guarded.written_confirmed is False
    assert guarded.has_fee_dispute is True
    assert analysis.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}
    assert "客户对收费规则的书面确认" in analysis.missing_evidence


def test_safety_incident_creates_high_risk_floor() -> None:
    source_text = (
        "客户李先生找老人陪护，老人有吞咽困难，存在噎食风险，"
        "责任边界和紧急联系人尚未确认。"
    )

    analysis = build_risk_analysis(
        source_text,
        apply_guardrails(source_text, ExtractedFacts()),
        "local-rules",
    )

    assert analysis.risk_level == RiskLevel.HIGH
    assert any("人身安全" in reason for reason in analysis.reasons)
    assert analysis.refusal_action is not None
