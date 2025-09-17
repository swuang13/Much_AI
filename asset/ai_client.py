import json
import logging
import re
from typing import Dict, List, Optional

from django.conf import settings
from huggingface_hub import InferenceClient


logger = logging.getLogger(__name__)


class _HFClientSingleton:
    _client: Optional[InferenceClient] = None
    _model: Optional[str] = None

    @classmethod
    def get_client(cls) -> Optional[InferenceClient]:
        if cls._client is not None:
            return cls._client
        api_key = getattr(settings, "HF_API_KEY", None)
        model = getattr(settings, "AI_MODEL_NAME", None)
        cls._model = model

        if not api_key or not model:
            logger.error("HF_API_KEY 또는 AI_MODEL_NAME 설정이 없습니다.")
            cls._client = None
            return None
        try:
            # Novita provider 사용 (사용자 제공 코드 준수)
            cls._client = InferenceClient(provider="novita", api_key=api_key)
            logger.info(f"HuggingFace InferenceClient 초기화 성공 - 모델: {model}")
        except Exception as e:
            logger.error(f"HuggingFace InferenceClient 초기화 실패: {e}")
            cls._client = None
        return cls._client

    @classmethod
    def get_model(cls) -> Optional[str]:
        if cls._model is None:
            _ = cls.get_client()
        return cls._model


def _extract_json_from_text(text: str) -> dict:
    """모델 응답에서 JSON 객체를 최대한 견고하게 추출/파싱."""
    t = (text or "").strip()
    # 코드펜스 제거
    for marker in ("```json", "```JSON", "```", "json", "JSON"):
        if t.startswith(marker):
            t = t[len(marker) :].strip()
        if t.endswith(marker):
            t = t[: -len(marker)].strip()
    # 가장 큰 JSON 블록 추출
    matches = re.findall(r"\{.*\}", t, re.DOTALL)
    json_str = max(matches, key=len) if matches else t
    return json.loads(json_str)


def hf_chat(system_prompt: str, user_content: str, *, max_tokens: int = 1200, temperature: float = 0.15, top_p: float = 0.9) -> str:
    """HF Chat 호출 후 순수 텍스트 응답 반환."""
    client = _HFClientSingleton.get_client()
    model = _HFClientSingleton.get_model()
    if not client or not model:
        raise RuntimeError("HF 클라이언트 또는 모델이 설정되지 않았습니다.")

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    if not completion or not getattr(completion, "choices", None):
        raise RuntimeError("HF 응답이 비어있습니다.")

    return completion.choices[0].message.content or ""


def hf_chat_json(system_prompt: str, user_content: str, *, max_tokens: int = 1800, temperature: float = 0.2, top_p: float = 0.9) -> dict:
    """HF Chat 호출 후 JSON 파싱하여 반환."""
    text = hf_chat(system_prompt, user_content, max_tokens=max_tokens, temperature=temperature, top_p=top_p)
    try:
        return json.loads(text)
    except Exception:
        pass
    # 보강 파싱
    try:
        return _extract_json_from_text(text)
    except Exception as e:
        snippet = (text or "")[:200]
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {snippet}") from e


