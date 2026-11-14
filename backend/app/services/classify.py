"""Complaint classification.

Default: transparent keyword rules (offline, no API key).
Optional: Gemini, when GEMINI_API_KEY is set. The API key never leaves the
backend, and any Gemini failure silently falls back to the rules.
"""

from __future__ import annotations

import json
import re

import requests

from .. import config
from ..constants import COMPLAINT_CATEGORIES, DEPARTMENTS, PRIORITIES

# category -> (department, keywords)
CATEGORY_RULES: dict[str, tuple[str, list[str]]] = {
    "Safety & Security": (
        "Campus Security",
        [
            "harass", "assault", "threat", "weapon", "fire", "smoke", "gas leak",
            "electric shock", "injur", "accident", "unsafe", "security", "stolen",
            "theft", "emergency", "collapse", "fight", "bully", "stalk",
            "bleeding", "exposed wire",
        ],
    ),
    "IT & Network": (
        "IT Services",
        [
            "wifi", "wi-fi", "internet", "network", "login", "password", "portal",
            "website", "computer", "laptop", "projector", "printer", "software",
            "email", "server", "online class", "zoom", "account",
        ],
    ),
    "Hostel": (
        "Hostel Administration",
        [
            "hostel", "dorm", "dormitory", "roommate", "warden", "bed", "shower",
            "hot water", "laundry", "residence",
        ],
    ),
    "Cleanliness": (
        "Sanitation Services",
        [
            "garbage", "trash", "rubbish", "dirty", "cleaning", "pest",
            "mosquito", "cockroach", "smell", "odor", "overflow", "litter",
        ],
    ),
    "Transport": (
        "Transport & Parking",
        [
            "bus", "shuttle", "parking", "car", "bike", "motorcycle", "traffic",
            "gate", "driver", "transport",
        ],
    ),
    "Academics": (
        "Academic Affairs",
        [
            "exam", "grade", "lecture", "course", "timetable", "schedule",
            "assignment", "professor", "lecturer", "registration", "transcript",
            "class", "curriculum", "semester",
        ],
    ),
    "Facilities": (
        "Facilities & Maintenance",
        [
            "leak", "water", "pipe", "plumbing", "electricity", "power", "light",
            "bulb", "fan", "air condition", "heating", "door", "window", "chair",
            "desk", "table", "bench", "roof", "ceiling", "floor", "elevator",
            "lift", "broken", "damage", "repair", "toilet",
        ],
    ),
}

CRITICAL_WORDS = [
    "fire", "smoke", "injur", "harass", "assault", "threat", "weapon",
    "gas leak", "electric shock", "collapse", "emergency", "bleeding",
]
HIGH_WORDS = [
    "leak", "flood", "no water", "power outage", "broken glass", "stuck",
    "elevator", "security", "stolen", "theft", "slippery", "mold",
    "exposed wire", "outage", "unsafe",
]
LOW_WORDS = ["suggestion", "request", "minor", "cosmetic", "slow", "noise", "sign", "paint"]

FALLBACK = {
    "category": "Other",
    "department": "Student Affairs",
    "priority": "Medium",
    "confidence": 0.35,
    "reason": "No strong category keywords found; routed to Student Affairs for review.",
    "source": "rules",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def _hits(text: str, keywords: list[str]) -> list[str]:
    return [word for word in keywords if word in text]


def classify_rules(description: str) -> dict:
    text = _normalize(description)
    if not text.strip():
        return dict(FALLBACK)

    critical = _hits(text, CRITICAL_WORDS)
    high = _hits(text, HIGH_WORDS)
    low = _hits(text, LOW_WORDS)

    # Weight safety-critical keywords so "harassment ... broken lights" is
    # routed to Campus Security, not Facilities, even if Facilities has more
    # incidental keyword hits.
    best_category = ""
    best_hits: list[str] = []
    best_weight = 0
    for category, (_, keywords) in CATEGORY_RULES.items():
        hits = _hits(text, keywords)
        weight = sum(3 if word in CRITICAL_WORDS else 1 for word in hits)
        if weight > best_weight:
            best_category, best_hits, best_weight = category, hits, weight

    if not best_category:
        result = dict(FALLBACK)
        result["reason"] = "No category keywords matched; please review the category manually."
        return result

    department = CATEGORY_RULES[best_category][0]
    if critical:
        priority = "Critical"
    elif high:
        priority = "High"
    elif low:
        priority = "Low"
    else:
        priority = "Medium"

    confidence = min(0.95, 0.5 + 0.1 * len(best_hits))
    reason_bits = []
    if best_hits:
        reason_bits.append("matched keywords: " + ", ".join(sorted(set(best_hits))[:5]))
    if critical:
        reason_bits.append("safety-critical wording")
    elif high:
        reason_bits.append("urgent wording")

    return {
        "category": best_category,
        "department": department,
        "priority": priority,
        "confidence": round(confidence, 2),
        "reason": "; ".join(reason_bits) or "Matched by keyword rules.",
        "source": "rules",
    }


def _classify_gemini(description: str) -> dict | None:
    if not config.GEMINI_API_KEY:
        return None

    prompt = (
        "You triage university campus complaints. Reply with JSON only, no markdown, "
        "using exactly these keys: category, department, priority, confidence, reason.\n"
        f"category must be one of: {', '.join(COMPLAINT_CATEGORIES)}.\n"
        f"department must be one of: {', '.join(DEPARTMENTS)}.\n"
        f"priority must be one of: {', '.join(PRIORITIES)}.\n"
        "confidence is a number from 0 to 1. reason is one short sentence.\n"
        f"Complaint: {description[:3000]}"
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
    )
    response = requests.post(
        url,
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        },
        timeout=15,
    )
    response.raise_for_status()
    raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(raw)

    if data.get("category") not in COMPLAINT_CATEGORIES:
        return None
    if data.get("department") not in DEPARTMENTS:
        return None
    if data.get("priority") not in PRIORITIES:
        return None

    confidence = float(data.get("confidence", 0.7))
    return {
        "category": data["category"],
        "department": data["department"],
        "priority": data["priority"],
        "confidence": max(0.0, min(1.0, confidence)),
        "reason": str(data.get("reason", "Classified by Gemini."))[:300],
        "source": "gemini",
    }


def classify_text(description: str) -> dict:
    fallback = classify_rules(description)
    if config.GEMINI_API_KEY:
        try:
            result = _classify_gemini(description)
            if result:
                return result
        except Exception:  # noqa: BLE001 - never fail a submission over the LLM
            pass
    return fallback
