from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class DependencyStatus(BaseModel):
    supabase: Literal["ok", "not_checked"] = "ok"
    openai: Literal["ok", "not_checked"] = "not_checked"
    github: Literal["ok", "not_checked"] = "not_checked"


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    dependencies: DependencyStatus


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="v1.0",
        dependencies=DependencyStatus(),
    )
