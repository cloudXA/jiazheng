import logging
from functools import lru_cache
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import Settings, get_settings
from app.schemas import ExtractedFacts, RiskAnalysis
from app.services.deepseek import DeepSeekExtractor
from app.services.rule_engine import (
    apply_guardrails,
    build_risk_analysis,
    extract_heuristic_facts,
)

logger = logging.getLogger(__name__)


class RiskWorkflowState(TypedDict, total=False):
    source_text: str
    facts: ExtractedFacts
    extraction_source: str
    analysis: RiskAnalysis


class RiskWorkflow:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._extractor = DeepSeekExtractor(settings) if settings.deepseek_configured else None

        builder = StateGraph(RiskWorkflowState)
        builder.add_node("extract_facts", self._extract_facts)
        builder.add_node("review_and_score", self._review_and_score)
        builder.add_edge(START, "extract_facts")
        builder.add_edge("extract_facts", "review_and_score")
        builder.add_edge("review_and_score", END)
        self._graph = builder.compile()

    async def _extract_facts(self, state: RiskWorkflowState) -> RiskWorkflowState:
        source_text = state["source_text"]
        if self._extractor is None:
            return {
                "facts": extract_heuristic_facts(source_text),
                "extraction_source": "本地规则",
            }

        try:
            facts = await self._extractor.extract(source_text)
            return {"facts": facts, "extraction_source": "DeepSeek + 规则复核"}
        except Exception as error:
            logger.warning(
                "DeepSeek extraction failed; using local fallback. error_type=%s",
                type(error).__name__,
            )
            return {
                "facts": extract_heuristic_facts(source_text),
                "extraction_source": "本地规则（模型调用失败）",
            }

    def _review_and_score(self, state: RiskWorkflowState) -> RiskWorkflowState:
        guarded_facts = apply_guardrails(state["source_text"], state["facts"])
        return {
            "facts": guarded_facts,
            "analysis": build_risk_analysis(
                state["source_text"],
                guarded_facts,
                state["extraction_source"],
            ),
        }

    async def analyze(self, source_text: str) -> RiskAnalysis:
        result = await self._graph.ainvoke({"source_text": source_text})
        analysis = result.get("analysis")
        if not isinstance(analysis, RiskAnalysis):
            raise RuntimeError("risk workflow did not produce a valid analysis")
        return analysis


@lru_cache
def get_risk_workflow() -> RiskWorkflow:
    return RiskWorkflow(get_settings())

