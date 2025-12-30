import datetime
from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel, field_validator

from ._base import BaseProvider


class AccessTokenResponse(BaseModel):
	access_token: str
	token_type: Literal["Bearer"]
	scope: list[str]
	created_at: datetime.datetime

	# noinspection PyNestedDecorators
	@field_validator("scope", mode="before")
	@classmethod
	def split_scope(cls, v: object) -> object:
		if isinstance(v, str):
			v = v.strip()
			return [] if v == "" else v.split(" ")
		return v


class GrantType(Enum):
	AUTHORIZATION_CODE = "authorization_code"
	CLIENT_CREDENTIALS = "client_credentials"


class OAuthProvider(BaseProvider):
	async def obtain_access_token(
		self,
		*,
		grant_type: GrantType,
		code: str,
		client_id: str,
		client_secret: str,
		redirect_uri: str,
		code_verifier: Optional[str] = None,
		scope: Optional[list[str]] = None
	) -> AccessTokenResponse:
		response = await self._session.request(
			method="POST",
			url=self._host_url / "oauth" / "token",
			json={
				"grant_type": grant_type.value,
				"code": code,
				"client_id": client_id,
				"client_secret": client_secret,
				"redirect_uri": redirect_uri,
				"code_verifier": code_verifier,
				"scope": " ".join(scope) if scope else None
			}
		)
		response.raise_for_status()
		return AccessTokenResponse(**await response.json())

	async def revoke_access_token(
			self,
			*,
			client_id: str,
			client_secret: str,
			token: str
	):
		response = await self._session.request(
			method="POST",
			url=self._host_url / "oauth" / "revoke",
			json={
				"client_id": client_id,
				"client_secret": client_secret,
				"token": token
			}
		)
		response.raise_for_status()
