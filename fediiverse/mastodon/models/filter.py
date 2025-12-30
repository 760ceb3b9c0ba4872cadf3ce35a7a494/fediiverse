from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from .filter_keyword import FilterKeyword
from .filter_status import FilterStatus


class FilterContext(Enum):
    HOME = "home"
    NOTIFICATIONS = "notifications"
    PUBLIC = "public"
    THREAD = "thread"
    ACCOUNT = "account"


class FilterAction(Enum):
    WARN = "warn"
    HIDE = "hide"
    BLUR = "blur"


class Filter(BaseModel):
    id: str
    title: str
    context: list[FilterContext]
    expires_at: Optional[datetime] = None
    filter_action: FilterAction
    keywords: Optional[list[FilterKeyword]] = None
    statuses: Optional[list[FilterStatus]] = None
