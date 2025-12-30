from typing import Optional

from pydantic import BaseModel, HttpUrl


class Application(BaseModel):
	id: str
	name: str
	website: Optional[HttpUrl] = None
	scopes: Optional[list[str]] = None
	redirect_uri: str
	redirect_uris: Optional[list[str]] = None
	client_id: str
	client_secret: str
