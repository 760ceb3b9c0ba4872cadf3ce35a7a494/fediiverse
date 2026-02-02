from typing import Optional, Any

from pydantic import BaseModel, HttpUrl

from ..models.rule import Rule


class InstanceThumbnail(BaseModel):
	url: HttpUrl
	blurhash: Optional[str] = None
	versions: Optional[dict] = None


class InstanceV2(BaseModel):
	domain: str
	title: str
	version: str
	source_url: str
	description: str
	usage: dict = {} # todo
	thumbnail: InstanceThumbnail
	languages: list[str] = []
	configuration: dict = {} # todo
	registrations: dict = {} # todo
	contact: dict = {} # todo
	rules: list[Rule] = []


class InstanceV1(BaseModel):
	uri: str
	title: str
	short_description: Optional[str] = None
	description: str
	email: str
	version: str
	urls: dict[str, str]  # todo
	stats: dict[str, Any]  # todo
	thumbnail: Optional[str] = None
	languages: list[str] = []
	registrations: bool
	approval_required: Optional[bool] = None
	invites_enabled: Optional[bool] = None
	configuration: dict[str, Any] = {}  # todo
	contact_account: Optional[dict] = None  # todo
	rules: list[Rule] = []
