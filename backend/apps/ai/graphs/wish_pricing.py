import json
import os
from pathlib import Path
from typing import Any

from django.conf import settings
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from apps.shop.models import ShopItemRarity, WishPriceTier
from apps.shop.services import PRICE_BOUNDS
from apps.users.models import DynamicProfile, StableProfile, User

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None


class WishPricingState(TypedDict, total=False):
    user_id: int
    source: str
    wish_payload: dict[str, Any]
    context_snapshot: dict[str, Any]
    profile_snapshot: dict[str, Any]
    pricing_standard: str
    pricing_standard_version: str
    quote_payload: dict[str, Any]


def round_5(value: float) -> int:
    return int(round(value / 5) * 5)


def _clamp(value: int, lower: int, upper: int) -> int:
    return min(max(value, lower), upper)


def load_profile(state: WishPricingState) -> dict[str, Any]:
    user = User.objects.get(pk=state["user_id"])
    StableProfile.objects.get_or_create(user=user)
    DynamicProfile.objects.get_or_create(user=user)
    return {"profile_snapshot": user.build_prompt_profile()}


def load_pricing_standard(state: WishPricingState) -> dict[str, Any]:
    path = Path(settings.BASE_DIR) / "apps" / "ai" / "prompts" / "wish_pricing_standard.md"
    return {
        "pricing_standard": path.read_text(encoding="utf-8"),
        "pricing_standard_version": "wish_pricing_v1",
    }


def _classify_tier(wish_payload: dict[str, Any]) -> str:
    explicit = wish_payload.get("price_tier")
    if explicit in WishPriceTier.values:
        return explicit

    text = " ".join(
        str(part).lower()
        for part in [
            wish_payload.get("title", ""),
            wish_payload.get("description", ""),
            " ".join(wish_payload.get("tags", []) or []),
        ]
    )
    large_keywords = ("travel", "trip", "hotel", "phone", "电脑", "旅行", "旅游", "演唱会", "高价值", "大件")
    medium_keywords = ("dinner", "restaurant", "meal", "spa", "外食", "餐厅", "聚餐", "按摩", "短途")
    small_keywords = ("coffee", "milk tea", "movie", "snack", "奶茶", "咖啡", "电影", "零食", "小奖励")
    if any(keyword in text for keyword in large_keywords):
        return WishPriceTier.LARGE
    if any(keyword in text for keyword in medium_keywords):
        return WishPriceTier.MEDIUM
    if any(keyword in text for keyword in small_keywords):
        return WishPriceTier.SMALL
    return WishPriceTier.MEDIUM


def _rarity_for_tier(tier: str) -> str:
    if tier == WishPriceTier.LARGE:
        return ShopItemRarity.EPIC
    if tier == WishPriceTier.MEDIUM:
        return ShopItemRarity.RARE
    return ShopItemRarity.COMMON


def _recommended_price(tier: str, source: str, context: dict[str, Any]) -> int:
    bounds = PRICE_BOUNDS[tier]
    midpoint = (bounds["min"] + bounds["max"]) / 2
    active_task_count = len(context.get("recent_active_tasks", []) or [])
    recent_wish_count = len(context.get("recent_wishes", []) or [])
    pressure_bonus = min(active_task_count * 0.03, 0.12)
    history_discount = min(recent_wish_count * 0.02, 0.08)
    refresh_discount = 0.10 if source == "daily_refresh" else 0
    price = midpoint * (1 + pressure_bonus - history_discount - refresh_discount)
    return _clamp(round_5(price), bounds["min"], bounds["max"])


def _fallback_wish_payload(state: WishPricingState, tier: str) -> dict[str, Any]:
    if state.get("wish_payload", {}).get("title"):
        return state["wish_payload"]

    recent_tasks = state.get("context_snapshot", {}).get("recent_active_tasks", [])
    if recent_tasks:
        task_title = recent_tasks[0].get("title", "近期目标")
        return {
            "title": f"完成《{task_title}》后的轻量奖励",
            "description": "系统根据近期任务压力生成的恢复型愿望奖励，确认后会加入你的愿望商店。",
            "price_tier": tier,
            "inventory": 1,
        }
    return {
        "title": "一次有边界的放松奖励",
        "description": "系统根据当前画像生成的通用愿望奖励，适合作为阶段性正反馈。",
        "price_tier": tier,
        "inventory": 1,
    }


def _baseline_quote(state: WishPricingState) -> dict[str, Any]:
    source = state.get("source", "manual")
    tier = _classify_tier(state.get("wish_payload", {}))
    wish_payload = _fallback_wish_payload(state, tier)
    tier = _classify_tier(wish_payload)
    bounds = PRICE_BOUNDS[tier]
    price = _recommended_price(tier, source, state.get("context_snapshot", {}))
    return {
        "title": wish_payload.get("title", ""),
        "description": wish_payload.get("description", ""),
        "price_tier": tier,
        "price_secondary": price,
        "rarity": wish_payload.get("rarity") or _rarity_for_tier(tier),
        "inventory": wish_payload.get("inventory", 1),
        "reasoning": (
            f"Classified as {tier} wish first, then priced at {price} within "
            f"{bounds['min']}-{bounds['max']} secondary currency."
        ),
        "risk_notes": [],
        "user_fit_notes": [
            "Daily refresh wishes include a small feedback discount."
            if source == "daily_refresh"
            else "Manual wish pricing follows the standard tier boundary."
        ],
        "pricing_bounds": {
            "price_secondary": {
                "min": bounds["min"],
                "max": bounds["max"],
                "recommended": price,
            },
            "price_tier": tier,
        },
        "llm_style_payload": {
            "source": source,
            "agent": "wish_pricing_v1",
            "context_task_count": len(state.get("context_snapshot", {}).get("recent_active_tasks", []) or []),
        },
    }


def _try_llm_refine_quote(state: WishPricingState, baseline_quote: dict[str, Any]) -> dict[str, Any]:
    if os.getenv("AI_PROVIDER", "mock") not in {"openai-compatible", "openai"}:
        return baseline_quote
    if ChatOpenAI is None or not os.getenv("AI_API_KEY"):
        return baseline_quote

    llm = ChatOpenAI(
        model=os.getenv("AI_MODEL", "gpt-4o-mini"),
        api_key=os.getenv("AI_API_KEY"),
        base_url=os.getenv("AI_BASE_URL") or None,
        temperature=float(os.getenv("AI_TEMPERATURE", "0.2")),
        timeout=int(os.getenv("AI_TIMEOUT", "60")),
        max_retries=int(os.getenv("AI_MAX_RETRIES", "2")),
    )
    prompt = f"""
You are the MotiWish wish pricing assistant. Classify wish tier first, then return JSON only.

Pricing standard:
{state.get("pricing_standard", "")}

User profile:
{json.dumps(state.get("profile_snapshot", {}), ensure_ascii=False)}

Context snapshot:
{json.dumps(state.get("context_snapshot", {}), ensure_ascii=False)}

Wish payload:
{json.dumps(state.get("wish_payload", {}), ensure_ascii=False)}

Baseline quote and hard bounds:
{json.dumps(baseline_quote, ensure_ascii=False)}
"""
    try:
        response = llm.invoke(prompt)
        parsed = json.loads(response.content)
        quote = {**baseline_quote, **parsed}
        tier = quote.get("price_tier") if quote.get("price_tier") in WishPriceTier.values else baseline_quote["price_tier"]
        bounds = PRICE_BOUNDS[tier]
        price = _clamp(round_5(float(quote.get("price_secondary", baseline_quote["price_secondary"]))), bounds["min"], bounds["max"])
        quote["price_tier"] = tier
        quote["price_secondary"] = price
        quote["pricing_bounds"] = {
            "price_secondary": {"min": bounds["min"], "max": bounds["max"], "recommended": price},
            "price_tier": tier,
        }
        quote["llm_style_payload"] = {
            **baseline_quote.get("llm_style_payload", {}),
            "provider": "openai-compatible",
        }
        return quote
    except Exception as exc:
        return {
            **baseline_quote,
            "risk_notes": [
                *baseline_quote.get("risk_notes", []),
                f"LLM refine failed, used local baseline: {str(exc)[:80]}",
            ],
        }


def draft_wish_quote(state: WishPricingState) -> dict[str, Any]:
    return {"quote_payload": _try_llm_refine_quote(state, _baseline_quote(state))}


def build_wish_pricing_graph():
    builder = StateGraph(WishPricingState)
    builder.add_node("load_profile", load_profile)
    builder.add_node("load_pricing_standard", load_pricing_standard)
    builder.add_node("draft_wish_quote", draft_wish_quote)
    builder.add_edge(START, "load_profile")
    builder.add_edge("load_profile", "load_pricing_standard")
    builder.add_edge("load_pricing_standard", "draft_wish_quote")
    builder.add_edge("draft_wish_quote", END)
    return builder.compile()
