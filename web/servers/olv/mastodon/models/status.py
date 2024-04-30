from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, HttpUrl
from datetime import datetime
from enum import Enum

from .account import Account
from .custom_emoji import CustomEmoji
from .filter_result import FilterResult
from .media_attachment import MediaAttachment
from .preview_card import PreviewCard


class StatusVisibility(Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"
    DIRECT = "direct"


class StatusApplication(BaseModel):
    name: str
    website: Optional[HttpUrl]


class StatusMention(BaseModel):
    id: str
    username: str
    url: HttpUrl
    acct: str


class StatusTag(BaseModel):
    name: str
    url: HttpUrl


class Status(BaseModel):
    id: str
    uri: HttpUrl
    created_at: datetime
    account: Account
    content: str
    visibility: StatusVisibility   # im so dumb lol
    sensitive: bool
    spoiler_text: str
    media_attachments: list[MediaAttachment]
    application: Optional[StatusApplication]
    mentions: list[StatusMention]
    tags: list[StatusTag]
    emojis: list[CustomEmoji]
    reblogs_count: int
    favourites_count: int
    replies_count: int
    url: Optional[HttpUrl]
    in_reply_to_id: Optional[str]
    in_reply_to_account_id: Optional[str]
    reblog: Optional[Status]
    # poll
    card: Optional[PreviewCard]
    language: Optional[str]
    text: Optional[str]
    edited_at: Optional[datetime]
    favourited: Optional[bool]
    reblogged: Optional[bool]
    muted: Optional[bool]
    bookmarked: Optional[bool]
    pinned: Optional[bool]
    filtered: list[FilterResult]
