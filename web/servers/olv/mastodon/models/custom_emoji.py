from typing import Optional

from pydantic import BaseModel, HttpUrl


class CustomEmoji(BaseModel):
    shortcode: str
    url: HttpUrl
    static_url: HttpUrl
    visible_in_picker: bool
    category: Optional[str]
