from typing import Optional

from pydantic import BaseModel
from .filter import Filter


class FilterResult(BaseModel):
    filter: Filter
    keyword_matches: Optional[list[str]]
    status_matches: Optional[list[str]]
