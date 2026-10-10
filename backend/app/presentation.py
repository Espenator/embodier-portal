"""Tier personalization — the presentation layer.

Every member-facing response carries a `presentation` block whose copy and
posture vary by tier. Endpoints never hardcode tier strings; they call
present(tier, key). Unknown tiers fall back to inner_circle voice.

Voices:
  inner_circle  — warm community voice ("welcome to the circle")
  equity_plus   — ownership voice ("your resort, your stake")
  capital_partner — institutional voice ("allocation", "diligence")
"""
from __future__ import annotations

TIERS = ("inner_circle", "equity_plus", "capital_partner")

_VOICES: dict[str, dict[str, str]] = {
    "inner_circle": {
        "greeting": "Welcome to the Inner Circle — you're in.",
        "portfolio_title": "Your piece of the collection",
        "portfolio_empty": ("Nothing here yet — your first Embodiment is "
                             "one tap away. The waitlist opens first."),
        "interests_title": "Resorts on your radar",
        "interests_cta": "Tap \"I want in\" on any offering and we'll hold "
                         "your place in line.",
        "documents_title": "Your documents",
        "exchange_note": ("The exchange opens to the waitlist first — you're "
                          "on the list, and we'll tell you the moment your "
                          "tier can trade."),
        "offering_push": "A new offering just opened for the Inner Circle.",
    },
    "equity_plus": {
        "greeting": "Your resort, your stake — welcome back.",
        "portfolio_title": "Your Embodiments",
        "portfolio_empty": ("No Embodiments yet. When your offering closes, "
                             "your stake appears here."),
        "interests_title": "Offerings you're tracking",
        "interests_cta": "Express interest to hold your allocation place.",
        "documents_title": "Your ownership documents",
        "exchange_note": ("Your Embodiments will be tradable on the exchange "
                          "at launch — the waitlist opens first."),
        "offering_push": "A new Equity Plus offering is open for allocation.",
    },
    "capital_partner": {
        "greeting": "Approved partner access confirmed.",
        "portfolio_title": "Allocation portfolio",
        "portfolio_empty": ("No active allocations. Approved partners see "
                             "every opportunity first."),
        "interests_title": "Indications of interest",
        "interests_cta": "Submit an indication to begin diligence.",
        "documents_title": "Diligence documents",
        "exchange_note": ("Exchange trading opens to the waitlist first; "
                          "partner allocations settle per offering terms."),
        "offering_push": "A new partner allocation opportunity is available.",
    },
}


def present(tier: str, key: str) -> str:
    voice = _VOICES.get(tier) or _VOICES["inner_circle"]
    return voice.get(key, "")


def voice_for(tier: str) -> dict[str, str]:
    return dict(_VOICES.get(tier) or _VOICES["inner_circle"])
