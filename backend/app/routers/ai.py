"""AI helpers exposed to the UI: live complaint triage and form options."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..constants import (
    COMPLAINT_CATEGORIES,
    DEPARTMENTS,
    ITEM_CATEGORIES,
    PRIORITIES,
)
from ..deps import get_current_user
from ..models import User
from ..schemas import ClassifyIn, SuggestionOut
from ..services.classify import classify_text

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/classify", response_model=SuggestionOut)
def classify(
    data: ClassifyIn,
    user: User = Depends(get_current_user),
) -> dict:
    return classify_text(data.description)


@router.get("/categories")
def categories(user: User = Depends(get_current_user)) -> dict:
    return {
        "item_categories": ITEM_CATEGORIES,
        "complaint_categories": COMPLAINT_CATEGORIES,
        "departments": DEPARTMENTS,
        "priorities": PRIORITIES,
    }
