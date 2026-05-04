from __future__ import annotations

import re
from typing import Iterable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.bot.entity_extractor import extract_entities
from app.bot.prompts import SYSTEM_PROMPT
from app.bot.tools import search_properties
from app.services.llm_factory import build_chat_openai


def _format_property_reply(items: list[dict], relaxed_budget: bool = False) -> str:
    if not items:
        return "Пока не вижу подходящих вариантов по этим параметрам. Могу предложить альтернативы по соседним районам или расширить бюджет."

    if relaxed_budget:
        lines = ["По району/ЖК нашёл варианты, но они выше указанного бюджета:"]
    else:
        lines = ["Нашёл подходящие варианты:"]

    for item in items:
        price = f'{item["price"]:,}'.replace(",", " ")

        lines.append(
            f'- {item["title"]}: {price} ₸, '
            f'{item["area_m2"]} м², {item["url"]}'
        )

    return "\n".join(lines)


def _build_room_availability_hint(
    *,
    district: str | None,
    residential_complex: str | None,
    max_budget: int | None,
    selected_items: list[dict],
) -> str | None:
    if max_budget is None or (not district and not residential_complex):
        return None

    all_items = search_properties.invoke(
        {
            "district": district,
            "residential_complex": residential_complex,
            "rooms": None,
            "max_budget": None,
        }
    )
    if not all_items:
        return None

    visible_rooms = {item["rooms"] for item in selected_items}
    missing_room_items = [item for item in all_items if item["rooms"] not in visible_rooms and item["price"] > max_budget]
    if not missing_room_items:
        return None

    cheapest_by_rooms: dict[int, dict] = {}
    for item in missing_room_items:
        rooms = item["rooms"]
        if rooms not in cheapest_by_rooms or item["price"] < cheapest_by_rooms[rooms]["price"]:
            cheapest_by_rooms[rooms] = item

    hints: list[str] = []
    for rooms, item in sorted(cheapest_by_rooms.items()):
        price = f'{item["price"]:,}'.replace(",", " ")
        hints.append(f"{rooms}-комн. от {price} ₸ ({item['url']})")

    if not hints:
        return None

    return "\nДополнительно: в этом районе есть варианты выше бюджета — " + "; ".join(hints)


def _is_selection_intent(user_message: str) -> bool:
    """Detect when user is selecting a specific listing, not requesting a fresh search."""
    lowered = user_message.lower()
    selection_markers = (
        "выбира",
        "беру",
        "подтверж",
        "хочу эту",
        "эту квартиру",
        "этот вариант",
    )
    has_selection_phrase = any(marker in lowered for marker in selection_markers)
    has_listing_reference = "ast-" in lowered or "/properties/" in lowered
    return has_selection_phrase and has_listing_reference


def _is_soft_selection_intent(user_message: str, conversation_history: Iterable[str] | None) -> bool:
    """Detect selection without explicit listing id/link in the current user message."""
    lowered = user_message.lower()
    selection_markers = (
        "выбира",
        "беру",
        "подтверж",
        "да, выбираю",
        "да выбираю",
        "ок, выбираю",
    )
    if not any(marker in lowered for marker in selection_markers):
        return False
    if not conversation_history:
        return False

    recent_history = list(conversation_history)[-6:]
    return any("ast-" in msg.lower() or "/properties/" in msg.lower() for msg in recent_history)


def _format_history(conversation_history: Iterable[str] | None) -> list[HumanMessage | AIMessage]:
    messages: list[HumanMessage | AIMessage] = []
    if not conversation_history:
        return messages

    for line in conversation_history:
        if line.startswith("assistant:"):
            messages.append(AIMessage(content=line.replace("assistant:", "", 1).strip()))
        else:
            messages.append(HumanMessage(content=line.replace("user:", "", 1).strip()))
    return messages


def run_agent(user_message: str, conversation_history: list[str] | None = None) -> str:
    """Run real-estate LangChain agent over an incoming user message."""

    extracted = extract_entities(user_message)
    if extracted.wants_manager:
        return "Понял вас, передаю диалог менеджеру."

    has_search_filters = bool(
        extracted.rooms is not None or extracted.budget is not None or extracted.district or extracted.residential_complex
    )
    if _is_selection_intent(user_message) or _is_soft_selection_intent(user_message, conversation_history):
        return (
            "Отлично, фиксирую выбор квартиры. Подтверждаю: вы выбираете этот объект. "
            "Далее уточню детали просмотра и передам менеджеру при необходимости."
        )
    if has_search_filters:
        if not extracted.district and not extracted.residential_complex:
            return "Уточните, пожалуйста, район или ЖК, чтобы я подобрал релевантные варианты."
        direct_items = search_properties.invoke(
            {
                "district": extracted.district,
                "residential_complex": extracted.residential_complex,
                "rooms": extracted.rooms,
                "max_budget": extracted.budget,
            }
        )
        if direct_items:
            reply = _format_property_reply(direct_items)
            room_hint = _build_room_availability_hint(
                district=extracted.district,
                residential_complex=extracted.residential_complex,
                max_budget=extracted.budget,
                selected_items=direct_items,
            )
            if room_hint:
                reply += room_hint
            return reply

        if extracted.budget is not None:
            relaxed_items = search_properties.invoke(
                {
                    "district": extracted.district,
                    "residential_complex": extracted.residential_complex,
                    "rooms": extracted.rooms,
                    "max_budget": None,
                }
            )
            if relaxed_items:
                return _format_property_reply(relaxed_items, relaxed_budget=True)

        return _format_property_reply([])

    llm = build_chat_openai(temperature=0.2)
    llm_with_tools = llm.bind_tools([search_properties])

    messages = [SystemMessage(content=SYSTEM_PROMPT), *_format_history(conversation_history), HumanMessage(content=user_message)]

    ai_message = llm_with_tools.invoke(messages)
    if not ai_message.tool_calls:
        return str(ai_message.content)

    tool_results: list[ToolMessage] = []
    for tool_call in ai_message.tool_calls:
        if tool_call.get("name") != "search_properties":
            continue

        tool_output = search_properties.invoke(tool_call.get("args", {}))
        if not tool_output:
            tool_output = [
                {
                    "status": "empty",
                    "message": "По заданным параметрам объектов не найдено. Предложи уточнить критерии.",
                }
            ]

        tool_results.append(
            ToolMessage(
                content=str(tool_output),
                tool_call_id=tool_call["id"],
            )
        )

    final_messages = [*messages, ai_message, *tool_results]
    final_answer = llm.invoke(final_messages)
    return str(final_answer.content)
