"""

This script sets up a fediiverse instance for the first time.
for details on setting up an instance , see docs/hosting/setup-instructions.md.

"""

import asyncio
import datetime
import io
import os
import platform
import re
import tarfile
from pathlib import Path

import aiohttp
import questionary
from cryptography.fernet import Fernet
from fediiverse.certificates import generate_certificates
from fediiverse.nginx import build_configuration

APP_NAME = "fediiverse"

# default options:
INSTANCE_PLACEHOLDER = "mastodon.social"
BLOCKLIST_URL = "https://raw.githubusercontent.com/gardenfence/blocklist/refs/heads/main/gardenfence.txt"
BLOCKLIST_CACHE_DURATION = datetime.timedelta(weeks=1)
CERTIFICATE_VALID_DAYS = 365*3  # 3 years


def get_default_fediiverse_path() -> Path:
	system = platform.system()

	if system == "Darwin":  # macOS
		return Path.home() / "Library" / "Application Support" / APP_NAME
	elif system == "Linux":
		return Path.home() / f".{APP_NAME}"
	elif system == "Windows":
		_appdata = os.getenv("AppData")
		if not _appdata:
			raise ValueError("failed to find %AppData%")
		return Path(_appdata) / APP_NAME
	else:
		raise ValueError(f"unknown system {system!r}")


# https://stackoverflow.com/a/33715765, modified
def validate_fqdn(dn):
	if dn.startswith("."):
		return False
	if dn.endswith("."):
		dn = dn[:-1]
	if len(dn) < 1 or len(dn) > 253:
		return False
	ldh_re = re.compile("^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
	return all(ldh_re.match(x) for x in dn.split("."))


async def download_twemoji(twemoji_dir: Path):
	async with aiohttp.ClientSession() as session:
		response = await session.get("https://github.com/jdecked/twemoji/tarball/main")
		response.raise_for_status()
		tar_gz_obj = io.BytesIO(await response.content.read())

		with tarfile.open(fileobj=tar_gz_obj, mode="r:gz") as file:
			namelist: list[str] = file.getnames()
			tar_root_dir_name: str | None = None
			for member_name in namelist:
				if "/" not in member_name:
					tar_root_dir_name = member_name
					break
			if not tar_root_dir_name:
				raise ValueError("failed to find root directory of tarball")

			assets_svg_dir_name = tar_root_dir_name + "/assets/svg"
			if assets_svg_dir_name not in namelist:
				raise ValueError("failed to find /assets/svg directory in tarball")

			twemoji_dir.mkdir()

			prefix = assets_svg_dir_name + "/"
			for member_name in namelist:
				if not member_name.startswith(prefix):
					continue
				filename = member_name.removeprefix(prefix)
				if "/" in filename:
					continue

				with open(twemoji_dir / filename, "wb") as stream:
					stream.write(file.extractfile(member=member_name).read())


async def main():
	questionary.print("Welcome to the fediiverse first-time setup!")

	# We need to figure out the config path BEFORE importing from fediiverse.storage
	fediiverse_path = os.getenv("FEDIIVERSE_ROOT_PATH")
	while not fediiverse_path:
		maybe_fediiverse_path = await questionary.path(
			message="Select a path for this fediiverse instance:",
			default=str(get_default_fediiverse_path()),
			only_directories=True
		).ask_async()
		if maybe_fediiverse_path is None:
			return

		maybe_fediiverse_path = Path(maybe_fediiverse_path).expanduser()
		if not maybe_fediiverse_path.parent.exists():
			questionary.print("No such path!")
			continue
		if maybe_fediiverse_path.exists() and not maybe_fediiverse_path.is_dir():
			questionary.print("Path already exists and is not a directory!")
			continue

		# path is satisfactory - try to bring it relative to user (~)
		try:
			fediiverse_path = Path("~") / maybe_fediiverse_path.relative_to(Path.home())
		except ValueError:
			# path cannot be made relative
			fediiverse_path = maybe_fediiverse_path

	os.environ["FEDIIVERSE_ROOT_PATH"] = str(fediiverse_path)

	from fediiverse.storage import FediiverseConfig, FediiverseConfigHosts, FediiverseConfigSecrets, set_config, \
		CERTIFICATES_PATH, FediiverseMode, FediiverseConfigInstances, FediiverseConfigWelcome, EMOJIS_PATH  # noqa: E402

	log_path = await questionary.path(
		message="Where would you like fediiverse nginx to store logs? (Make sure this directory exists!)",
		default="/var/log/nginx/fediiverse",
		only_directories=True
	).ask_async()
	if log_path is None:
		return
	log_path = Path(log_path)

	# handle fediiverse hosts
	while True:
		main_host = await questionary.text(
			"At what domain name will your fediiverse instance be located?",
			validate=lambda text: validate_fqdn(text) and len(f"https://d.{text}/v") <= 46
		).ask_async()
		if main_host is None:
			return

		discovery_host = f"d.{main_host}"
		olv_host = f"olv.{main_host}"
		img_host = f"img.{main_host}"
		setup_host = f"setup.{main_host}"
        setup_port = 80

		questionary.print("OK, the following domain names will be used:", style="bold")
		questionary.print(f"- {main_host}")
		questionary.print(f"- {discovery_host}")
		questionary.print(f"- {olv_host}")
		questionary.print(f"- {img_host}")
		questionary.print(f"- {setup_host}")

		confirmed = await questionary.confirm("Is that OK?").ask_async()
		if confirmed is None:
			return
		if confirmed:
			break

	# download twemoji
	if not EMOJIS_PATH.exists():
		await download_twemoji(EMOJIS_PATH)

	wants_upstream = await questionary.confirm(
		"Would you like to specify an upstream HTTPS server to proxy?",
		default=False
	).ask_async()
	if wants_upstream:
		proxy_upstream_https = await questionary.text(
			"What socket address would you like to make upstream?",
			default="127.0.0.1:8443"
		).ask_async()
	else:
		proxy_upstream_https = None

	# save config
	# noinspection PyTypeChecker
	config = FediiverseConfig(
		log_path=log_path,
		proxy_upstream_https=proxy_upstream_https,
		hosts=FediiverseConfigHosts(
			common_name=f"*.{main_host}",
			welcome_host=main_host,
			discovery_host=discovery_host,
			olv_host=olv_host,
			img_host=img_host,
			setup_host=setup_host
            setup_port=setup_port
		),
		secrets=FediiverseConfigSecrets(
			session_token_secret_key=Fernet.generate_key().decode("ascii"),
			temporal_secret_key=Fernet.generate_key().decode("ascii")
		),
		instances=FediiverseConfigInstances(
			blocklist=None,
			blocklist_url=BLOCKLIST_URL,
			blocklist_cache_duration=BLOCKLIST_CACHE_DURATION,
			allowlist=None,
			allowlist_dropdown=True,
			instance_placeholder=INSTANCE_PLACEHOLDER
		),
		welcome=FediiverseConfigWelcome(
			additional_intro_html=None
		),
		mode=FediiverseMode.PROD
	)
	set_config(config)

	# generate keys and certificates:
	CERTIFICATES_PATH.mkdir(exist_ok=True)
	generate_certificates(
		certificates_path=CERTIFICATES_PATH,
		organization_name=f"fediiverse: {main_host}",

		ca_cert_common_name=f"fediiverse root CA: {main_host}",
		ca_cert_valid_days=CERTIFICATE_VALID_DAYS,

		leaf_cert_common_name=f"*.{main_host}",  # must match your domain or it won't work!
		leaf_cert_valid_days=CERTIFICATE_VALID_DAYS
	)

	# update NGINX conf:
	build_configuration()

	questionary.print(f"your fediiverse server has been set up in {fediiverse_path}! ", style="pink bold")
	questionary.print(f"for further instruction, see ./docs/hosting/setup-instructions.md and configuration.md.",
					  style="pink bold")


if __name__ == "__main__":
	asyncio.run(main())
