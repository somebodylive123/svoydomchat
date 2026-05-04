from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel

from app.core.astana_districts import extract_astana_district_from_text, normalize_astana_district
from app.services.llm_factory import build_chat_openai


class PurchasePurpose(StrEnum):
    LIVING = "living"
    INVESTMENT = "investment"
    UNKNOWN = "unknown"


class LeadExtractedData(BaseModel):
    budget: int | None = None
    rooms: int | None = None
    district: str | None = None
    residential_complex: str | None = None
    purchase_purpose: PurchasePurpose = PurchasePurpose.UNKNOWN
    wants_manager: bool = False


_MANAGER_PATTERN = re.compile(r"\b(менеджер|позвоните|свяж\w*)\b", re.IGNORECASE)
_ROOM_PATTERNS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"\b1\s*[- ]?комнат\w*\b", re.IGNORECASE), 1),
    (re.compile(r"\b2\s*[- ]?комнат\w*\b", re.IGNORECASE), 2),
    (re.compile(r"\b3\s*[- ]?комнат\w*\b", re.IGNORECASE), 3),
    (re.compile(r"\b4\s*[- ]?комнат\w*\b", re.IGNORECASE), 4),
    (re.compile(r"\b1\s*комнат\w*\b", re.IGNORECASE), 1),
    (re.compile(r"\b2\s*комнат\w*\b", re.IGNORECASE), 2),
    (re.compile(r"\b3\s*комнат\w*\b", re.IGNORECASE), 3),
    (re.compile(r"\b4\s*комнат\w*\b", re.IGNORECASE), 4),
    (re.compile(r"\bоднушк\w*\b", re.IGNORECASE), 1),
    (re.compile(r"\bдвушк\w*\b", re.IGNORECASE), 2),
    (re.compile(r"\bтрешк\w*\b", re.IGNORECASE), 3),
)


def _extract_budget(text: str) -> int | None:
    lowered = text.lower()

    up_to_million = re.search(r"до\s*(\d+[\d\s]*)\s*млн", lowered)
    if up_to_million:
        value = int(up_to_million.group(1).replace(" ", ""))
        return value * 1_000_000

    million = re.search(r"(\d+[\d\s]*)\s*миллион", lowered)
    if million:
        value = int(million.group(1).replace(" ", ""))
        return value * 1_000_000

    mln = re.search(r"\b(\d+[\d\s]*)\s*млн\b", lowered)
    if mln:
        value = int(mln.group(1).replace(" ", ""))
        return value * 1_000_000

    raw_budget = re.search(r"\b(\d{7,9})\b", lowered)
    if raw_budget:
        return int(raw_budget.group(1))

    return None


def _extract_rooms(text: str) -> int | None:
    for pattern, rooms in _ROOM_PATTERNS:
        if pattern.search(text):
            return rooms
    return None


def _extract_purchase_purpose(text: str) -> PurchasePurpose:
    lowered = text.lower()
    if re.search(r"\b(для\s+жизни|жить|себ[ея])\b", lowered):
        return PurchasePurpose.LIVING
    if re.search(r"\b(инвестиц\w*|инвест\w*|доход)\b", lowered):
        return PurchasePurpose.INVESTMENT
    return PurchasePurpose.UNKNOWN


def _normalize_district_name(district: str | None) -> str | None:
    """Normalize district name through centralized Astana district registry."""
    return normalize_astana_district(district)


def _extract_district(text: str) -> str | None:
    direct_match = extract_astana_district_from_text(text)
    if direct_match:
        return direct_match

    match = re.search(r"(?:район(?:е)?\s+|в\s+районе\s+)([А-Яа-яЁё\-\s]+?)(?:,|\.|$)", text, re.IGNORECASE)
    if not match:
        return None

    district = match.group(1).strip()
    return _normalize_district_name(district)


def _normalize_budget_from_text(text: str, budget: int | None) -> int | None:
    if budget is None:
        return None

    lowered = text.lower()
    if budget < 1_000_000 and re.search(r"\b(млн|миллион\w*)\b", lowered):
        return budget * 1_000_000

    return budget


def _extract_residential_complex(text: str) -> str | None:
    patterns = (
        r"\bжк\s+([A-Za-zА-Яа-яЁё0-9\-\s]+?)(?:,|\.|$)",
        r"\bжил(?:ой|ого)?\s+комплекс(?:е|а)?\s+([A-Za-zА-Яа-яЁё0-9\-\s]+?)(?:,|\.|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip().strip('"“”')
            if value:
                return re.sub(r"\s+", " ", value)
    return None


def _fallback_extract(text: str) -> LeadExtractedData:
    return LeadExtractedData(
        budget=_extract_budget(text),
        rooms=_extract_rooms(text),
        district=_extract_district(text),
        residential_complex=_extract_residential_complex(text),
        purchase_purpose=_extract_purchase_purpose(text),
        wants_manager=bool(_MANAGER_PATTERN.search(text)),
    )


def extract_entities(text: str) -> LeadExtractedData:
    """Extract user intent and lead entities.

    Uses LLM structured output when LangChain/OpenAI are available.
    Falls back to regex extraction when unavailable or on any LLM failure.
    """
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
    except Exception:
        return _fallback_extract(text)

    try:
        llm = build_chat_openai(temperature=0)
        structured_llm = llm.with_structured_output(LeadExtractedData)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Extract real-estate lead fields from the user message. "
                    "Keep unknown fields null, and use purchase_purpose="
                    "living/investment/unknown.",
                ),
                ("human", "{message}"),
            ]
        )
        chain = prompt | structured_llm
        extracted = chain.invoke({"message": text})
        extracted.wants_manager = bool(_MANAGER_PATTERN.search(text))
        extracted.budget = _normalize_budget_from_text(text, extracted.budget)
        extracted.district = _normalize_district_name(extracted.district)
        if not extracted.district:
            extracted.district = _extract_district(text)
        if not extracted.residential_complex:
            extracted.residential_complex = _extract_residential_complex(text)
        return extracted
    except Exception:
        return _fallback_extract(text)
