from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator

from .custom_emoji import CustomEmoji


class AccountField(BaseModel):
    name: str
    value: str
    verified_at: Optional[datetime] = None


class Account(BaseModel):
    id: str
    username: str
    acct: str
    url: HttpUrl
    display_name: str
    note: str
    avatar: HttpUrl
    avatar_static: HttpUrl
    header: HttpUrl
    header_static: HttpUrl
    locked: bool
    fields: list[AccountField]
    emojis: list[CustomEmoji]
    bot: bool
    group: Optional[bool] = None
    discoverable: Optional[bool] = None
    noindex: Optional[bool] = None
    moved: Optional[Account] = None
    suspended: Optional[bool] = None
    limited: Optional[bool] = None
    created_at: datetime
    last_status_at: Optional[date] = None
    statuses_count: int
    followers_count: int
    following_count: int

    @field_validator("emojis", mode="before")
    @classmethod
    def remove_null_emojis(cls, data: Any) -> Any:
        # Fix for GoToSocial emoji objects with empty url values
        if isinstance(data, list):
            return [emoji_data for emoji_data in data if emoji_data["url"]]
        raise ValueError

