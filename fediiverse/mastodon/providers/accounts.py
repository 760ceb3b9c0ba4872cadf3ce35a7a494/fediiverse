from typing import Optional

from ._base import BaseProvider
from ..models.account import Account
from ..models.status import Status


class AccountsProvider(BaseProvider):
	async def get_local_account(self) -> Account:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "accounts" / "verify_credentials"
		)
		response.raise_for_status()
		return Account(**(await response.json()))

	async def lookup_account(self, acct: str) -> Account:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "accounts" / "lookup" % {
				"acct": acct
			}
		)
		response.raise_for_status()
		return Account(**(await response.json()))

	async def get_account(self, account_id: str) -> Account:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "accounts" / account_id
		)
		response.raise_for_status()
		return Account(**(await response.json()))

	async def get_account_statuses(
		self,
		account_id: str,
		max_id: Optional[str] = None,
		since_id: Optional[str] = None,
		min_id: Optional[str] = None,
		limit: Optional[int] = None,
		only_media: Optional = False,
		exclude_replies: bool = False,
		exclude_reblogs: bool = False,
		pinned: bool = False,
		tagged: Optional[str] = None
	) -> list[Status]:
		# yarl doesnt accept None values in params so i have to just do this
		params = {
			"only_media": "true" if only_media else "false",
			"exclude_replies": "true" if exclude_replies else "false",
			"exclude_reblogs": "true" if exclude_reblogs else "false",
			"pinned": "true" if pinned else "false",
		}
		if max_id is not None:
			params["max_id"] = max_id
		if since_id is not None:
			params["since_id"] = since_id
		if min_id is not None:
			params["min_id"] = min_id
		if limit is not None:
			params["limit"] = str(limit)
		if tagged is not None:
			params["tagged"] = tagged

		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "accounts" / account_id / "statuses" % params
		)
		response.raise_for_status()
		return [Status(**data) for data in await response.json()]
