from __future__ import annotations
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, HttpUrl

from .custom_emoji import CustomEmoji


class AccountField(BaseModel):
    name: str
    value: str
    verified_at: Optional[datetime]


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
    group: bool
    discoverable: Optional[bool]
    noindex: Optional[bool]
    moved: Optional[Account]
    suspended: Optional[bool]
    limited: Optional[bool]
    created_at: datetime
    last_status_at: Optional[date]
    statuses_count: int
    followers_count: int
    following_count: int
