"""Pydantic request/response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ReportStatusIn(BaseModel):
    status: Literal["open", "matched", "returned", "closed"]


class ComplaintUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=40)
    department: str | None = Field(default=None, max_length=60)
    priority: Literal["Low", "Medium", "High", "Critical"] | None = None
    status: Literal["Received", "In Progress", "Resolved"] | None = None
    admin_note: str | None = Field(default=None, max_length=2000)


class MatchReviewIn(BaseModel):
    status: Literal["approved", "rejected"]


class ClassifyIn(BaseModel):
    description: str = Field(min_length=3, max_length=4000)


class SuggestionOut(BaseModel):
    category: str
    department: str
    priority: str
    confidence: float
    reason: str
    source: str = "rules"
