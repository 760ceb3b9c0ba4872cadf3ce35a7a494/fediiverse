from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, HttpUrl

from ..models.rule import Rule


class InstanceThumbnail(BaseModel):
	url: HttpUrl
	blurhash: Optional[str]
	versions: Optional[dict]


class Instance(BaseModel):
	domain: str
	title: str
	version: str
	source_url: str
	description: str
	usage: dict  # todo
	thumbnail: InstanceThumbnail
	languages: list[str]
	configuration: dict  # todo
	registrations: dict  # todo
	contact: dict  # todo
	rules: list[Rule]
