import json

from openai import AsyncOpenAI

from app.config import Settings
from app.schemas import ExtractedFacts

SYSTEM_PROMPT = """
你是家政服务订单的信息提取器，不是律师，也不负责给出风险等级。
请根据用户提供的原始口述，仅提取明确出现的事实，并输出一个 JSON 对象。
不得补充、猜测或虚构原文没有的信息。没有明确说明的字符串填 null，布尔值填 false。
对于“还没有微信确认”“退款规则没说清”等否定表达，对应布尔值必须为 false。

JSON 必须严格包含以下字段：
{
  "customer_name": "客户称呼或 null",
  "service_type": "老人照护/育儿服务/钟点服务/保洁服务/住家服务或 null",
  "trial_days": 7,
  "worker_source": "公司阿姨/合作阿姨/第三方阿姨或 null",
  "charge_method": "按首月工资比例/固定金额/年费或 null",
  "charge_value": "30%/1000元或 null",
  "written_confirmed": false,
  "decision_maker_confirmed": false,
  "no_bypass_confirmed": false,
  "refund_explained": false,
  "care_safety_confirmed": false,
  "has_fee_dispute": false,
  "has_safety_event": false
}
""".strip()


class DeepSeekExtractor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=settings.deepseek_timeout_seconds,
        )

    async def extract(self, source_text: str) -> ExtractedFacts:
        response = await self._client.chat.completions.create(
            model=self._settings.deepseek_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"请输出 JSON：\n{source_text}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=1200,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("DeepSeek returned empty JSON content")
        payload = json.loads(content)
        return ExtractedFacts.model_validate(payload)

