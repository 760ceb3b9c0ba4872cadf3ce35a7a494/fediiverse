"""

Check instance domain names against allowlists and blocklists

"""

import datetime
import warnings
from typing import Optional

import aiofiles
import aiohttp
from pydantic import BaseModel

from .storage import get_config, CACHED_BLOCKLIST_PATH

config = get_config()


class CachedBlocklist(BaseModel):
	last_modified: datetime.datetime
	url: str
	blocklist: list[str]


async def download_blocklist() -> list[str]:
	print(f"Downloading blocklist from {config.instances.blocklist_url}")
	if config.instances.blocklist_url is None:
		raise ValueError("no blocklist URL")

	async with aiohttp.ClientSession() as session:
		response = await session.request("GET", str(config.instances.blocklist_url))
		response.raise_for_status()
		text = await response.text()

	lines = text.splitlines()
	lines = [line for line in lines if line]
	return lines


async def get_cached_blocklist() -> Optional[CachedBlocklist]:
	if not CACHED_BLOCKLIST_PATH.exists():
		return None

	try:
		async with aiofiles.open(CACHED_BLOCKLIST_PATH, "r") as file:
			return CachedBlocklist.model_validate_json(await file.read())
	except ValueError as e:
		warnings.warn(f"Cached blocklist malformed or invalid: {e}")
		return None


def check_should_use_cached_blocklist(cached_blocklist: CachedBlocklist):
	time_since_update = datetime.datetime.now(datetime.timezone.utc) - cached_blocklist.last_modified
	return (
			cached_blocklist.url == str(config.instances.blocklist_url)
			and (
				time_since_update < config.instances.blocklist_cache_duration
				if config.instances.blocklist_cache_duration else True
			)
	)


async def download_new_cached_blocklist() -> CachedBlocklist:
	blocklist = await download_blocklist()
	return CachedBlocklist(
		last_modified=datetime.datetime.now(datetime.timezone.utc),
		url=str(config.instances.blocklist_url),
		blocklist=blocklist
	)


async def save_cached_blocklist(cached_blocklist: CachedBlocklist):
	async with aiofiles.open(CACHED_BLOCKLIST_PATH, "w") as file:
		await file.write(cached_blocklist.model_dump_json())


async def get_blocklist() -> list[str]:
	cached_blocklist = await get_cached_blocklist()
	should_use_cached_blocklist = check_should_use_cached_blocklist(cached_blocklist) if cached_blocklist else None

	if not should_use_cached_blocklist:
		try:
			new_cached_blocklist = await download_new_cached_blocklist()
			await save_cached_blocklist(new_cached_blocklist)
			return new_cached_blocklist.blocklist
		except (ValueError, aiohttp.ClientError) as exception:
			warnings.warn(f"Failed to download new cached blocklist! {exception}")

	if cached_blocklist:
		if not should_use_cached_blocklist:
			warnings.warn("Using old blocklist even though it is outdated. Make sure the blocklist is reachable.")
		return cached_blocklist.blocklist

	raise ValueError("Failed to find usable blocklist")


async def is_allowed_instance_domain_name(domain_name: str) -> bool:
	# validate instance domain name against config.
	domain_name = domain_name.lower()  # case insensitive
	if config.instances.allowlist and domain_name not in config.instances.allowlist:
		return False

	if config.instances.blocklist and domain_name in config.instances.blocklist:
		return False

	if config.instances.blocklist_url:
		blocklist = await get_blocklist()
		if domain_name in blocklist:
			return False

	return True
