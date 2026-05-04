from __future__ import annotations

import re

_CANONICAL_DISTRICTS: dict[str, tuple[str, ...]] = {
    "Есиль": (
        "есиль",
        "есильский",
        "есильском",
        "есильского",
        "экспо",
        "триумфальная арка",
        "левый берег",
        "есиля",
        "Есиля"
    ),
    "Нура": (
        "нура",
        "нуринский",
        "нуринском",
        "нуринского",
        "нуры"
    ),
    "Алматы": (
        "алматы",
        "алматинский",
        "алматинском",
        "алматинского",
    ),
    "Сарыарка": (
        "сарыарка",
        "сарыаркинский",
        "сарыаркинском",
        "сарыаркинского",
    ),
    "Сарайшык": (
        "сарайшык",
        "сарайшыке",
        "сарайшыка",
        "сарышык",
        "saraishyq",
        "sarayshyk",
        "сарайчик",
    ),
    "Байконыр": (
        "байконыр",
        "байконур",
        "байконырском",
        "байконурском",
        "байконырского",
        "байконурского",
    ),
}


def _normalize_text(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    lowered = re.sub(r"[^\w\s-]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def normalize_astana_district(value: str | None) -> str | None:
    if not value:
        return None

    normalized = _normalize_text(value)
    if not normalized:
        return None

    if re.search(r"ботаническ\w*\s+(сад\w*|парк\w*)", normalized):
        return "Ботанический сад"

    if normalized in {"астана", "г астана", "город астана", "по астане", "в астане"}:
        return None

    for canonical, aliases in _CANONICAL_DISTRICTS.items():
        for alias in aliases:
            if alias in normalized or normalized in alias:
                return canonical

    return value.strip().title()


def extract_astana_district_from_text(text: str) -> str | None:
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return None

    if re.search(r"ботаническ\w*\s+(сад\w*|парк\w*)", normalized_text):
        return "Ботанический сад"

    for canonical, aliases in _CANONICAL_DISTRICTS.items():
        if any(alias in normalized_text for alias in aliases):
            return canonical

    return None
