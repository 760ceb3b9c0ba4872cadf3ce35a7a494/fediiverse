import asyncio

import questionary
from cryptography.fernet import Fernet

from fediiverse.storage import get_config, set_config, FediiverseConfigSecrets


async def main():
	response = await questionary.confirm("Are you sure you want to refresh secrets? This will log all users out of fediiverse.", default=False).ask_async()
	if not response:
		return
	secrets = FediiverseConfigSecrets(
		session_token_secret_key=Fernet.generate_key().decode("ascii"),
		temporal_secret_key=Fernet.generate_key().decode("ascii")
	)
	config = get_config()
	config.secrets = secrets
	set_config(config)
	questionary.print("Refreshed secrets.")

if __name__ == "__main__":
	asyncio.run(main())
