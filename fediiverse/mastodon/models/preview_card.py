from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PreviewCardType(Enum):
	LINK = "link"
	PHOTO = "photo"
	VIDEO = "video"
	RICH = "rich"  # not allowed


class PreviewCard(BaseModel):
	url: Optional[str] = None
	title: str
	description: str
	type: PreviewCardType
	author_name: Optional[str] = None
	author_url: Optional[str] = None
	provider_name: str
	provider_url: Optional[str] = None
	html: Optional[str] = None
	width: int = 0
	height: int = 0
	image: Optional[str] = None
	embed_url: Optional[str] = None
	blurhash: Optional[str] = None
