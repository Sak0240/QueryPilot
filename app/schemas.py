from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OptimizeRequest(BaseModel):
    sql: str = Field(..., min_length=1, max_length=10_000)
    dialect: Literal["postgres"] = "postgres"

    @field_validator("sql")
    @classmethod
    def strip_sql(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("SQL must not be empty")
        return v