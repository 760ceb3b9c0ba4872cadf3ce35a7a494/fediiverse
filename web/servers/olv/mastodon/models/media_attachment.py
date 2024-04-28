from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, HttpUrl


class MediaAttachmentType(Enum):
	UNKNOWN = "unknown"
	IMAGE = "image"
	GIFV = "gifv"
	VIDEO = "video"
	AUDIO = "audio"


class MediaAttachment(BaseModel):
	id: str
	type: MediaAttachmentType
	url: HttpUrl
	preview_url: Optional[HttpUrl]
	remote_url: Optional[HttpUrl]
	meta: Optional[dict[str, Any]]
	description: Optional[str]
	blurhash: Optional[str]
