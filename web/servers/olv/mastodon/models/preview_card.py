from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, HttpUrl


class PreviewCardType(Enum):
	LINK = "link"
	PHOTO = "photo"
	VIDEO = "video"
	RICH = "rich"  # not allowed


class PreviewCard(BaseModel):
	url: Optional[str]
	title: str
	description: str
	type: PreviewCardType
	author_name: str
	author_url: Optional[str]
	provider_name: str
	provider_url: Optional[str]
	html: str
	width: int
	height: int
	image: Optional[str]
	embed_url: Optional[str]
	blurhash: Optional[str]
