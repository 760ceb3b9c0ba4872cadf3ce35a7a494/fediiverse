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
	preview_url: Optional[HttpUrl] = None
	remote_url: Optional[HttpUrl] = None
	meta: Optional[dict[str, Any]] = None
	description: Optional[str] = None
	blurhash: Optional[str] = None
