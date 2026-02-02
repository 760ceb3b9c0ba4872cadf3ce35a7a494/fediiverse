"""

provides storage paths for fediiverse servers

For config schema see docs/hosting/configuration.md

"""
import datetime
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import aiosqlite
from pydantic import BaseModel, HttpUrl

APP_NAME = "fediiverse"

if "FEDIIVERSE_ROOT_PATH" not in os.environ:
	raise ValueError("FEDIIVERSE_ROOT_PATH not specified")

ROOT_PATH = Path(os.getenv("FEDIIVERSE_ROOT_PATH")).expanduser()

if not ROOT_PATH.is_dir():
	raise ValueError("FEDIIVERSE_ROOT_PATH is invalid")

CERTIFICATES_PATH = ROOT_PATH / "certificates"
CONFIG_PATH = ROOT_PATH / "config.json"
SQLITE_PATH = ROOT_PATH / "storage.db"
NGINX_PATH = ROOT_PATH / "nginx"
EMOJIS_PATH = ROOT_PATH / "emojis"
CACHED_BLOCKLIST_PATH = ROOT_PATH / "cached-blocklist.json"


@dataclass
class SavedInstance:
	domain_name: str
	client_id: str
	client_secret: str
	created_at: datetime.datetime


class FediiverseConfigHosts(BaseModel):
	common_name: str
	welcome_host: str
	discovery_host: str
	olv_host: str
	img_host: str
	setup_host: str
	setup_port: int = 80


class FediiverseConfigSecrets(BaseModel):
	temporal_secret_key: str
	session_token_secret_key: str


class FediiverseMode(Enum):
	PROD = "PROD"
	DEV = "DEV"


class FediiverseConfigInstances(BaseModel):
	blocklist: Optional[list[str]]
	blocklist_url: Optional[HttpUrl]
	blocklist_cache_duration: Optional[datetime.timedelta]

	allowlist: Optional[list[str]]
	allowlist_dropdown: bool

	instance_placeholder: str


class FediiverseConfigWelcome(BaseModel):
	additional_intro_html: Optional[str]


class FediiverseConfig(BaseModel):
	log_path: Path
	proxy_upstream_https: Optional[str] = None
	hosts: FediiverseConfigHosts
	secrets: FediiverseConfigSecrets
	instances: FediiverseConfigInstances
	welcome: FediiverseConfigWelcome
	mode: FediiverseMode


def get_config() -> FediiverseConfig:
	with open(CONFIG_PATH, "r") as file:
		return FediiverseConfig.model_validate_json(file.read())


def set_config(config: FediiverseConfig):
	with open(CONFIG_PATH, "w") as file:
		file.write(config.model_dump_json(indent=2))


class FediiverseStore:
	def __init__(self):
		self.sqlite: aiosqlite.Connection

	async def get_saved_instance(self, domain_name: str) -> SavedInstance | None:
		result = await (await self.sqlite.execute("SELECT * FROM instances WHERE domain_name = ?", (domain_name,))).fetchone()
		if result is None:
			return None

		domain_name, created_stamp, client_id, client_secret = result
		return SavedInstance(
			domain_name=domain_name,
			created_at=datetime.datetime.fromtimestamp(
				timestamp=created_stamp,
				tz=datetime.timezone.utc
			),
			client_id=client_id,
			client_secret=client_secret
		)

	async def save_instance(self, instance: SavedInstance) -> SavedInstance | None:
		await self.sqlite.execute(
			"INSERT INTO instances (domain_name, created_at, client_id, client_secret) VALUES (?,?,?,?)",
			(
				instance.domain_name,
				int(instance.created_at.timestamp()),
				instance.client_id,
				instance.client_secret
			)
		)
		await self.sqlite.commit()

	async def _setup(self):
		await self.sqlite.execute(
			"CREATE TABLE IF NOT EXISTS instances ("
			"  domain_name TEXT PRIMARY KEY,"
			"  created_at INTEGER,"
			"  client_id TEXT NOT NULL,"
			"  client_secret TEXT NOT NULL"
			")"
		)

	async def __aenter__(self):
		self.sqlite = await aiosqlite.connect(SQLITE_PATH)
		await self._setup()
		return self

	async def __aexit__(self, *_):
		await self.sqlite.close()
