"""

This code builds an nginx configuration based on the template in ./_template.
a simple templating system is implemented with the following pattern:
instances of `${KEY}` in ./_template/FILE.XYZ map to some `VALUE` in ./configuration/FILE.XYZ.
a list of valid keys is below in the template_params dict.
"""


import re
import shutil
from pathlib import Path


root_dir = Path(__file__).parent
template_dir = root_dir / "_template"

pattern = re.compile(r"\$\{(.+?)\}")


def build_configuration(log: bool = False):
	from fediiverse.storage import get_config, NGINX_PATH
	config = get_config()

	if NGINX_PATH.exists():
		shutil.rmtree(NGINX_PATH, ignore_errors=True)

	NGINX_PATH.mkdir(exist_ok=True)

	template_params = {
		"log_path": str(config.log_path.expanduser()),
		"proxy_upstream_https": str(config.proxy_upstream_https),
		"proxy_upstream_https_comment": "" if config.proxy_upstream_https else "# ",

		"discovery_host": config.hosts.discovery_host,
		"olv_host": config.hosts.olv_host,
		"img_host": config.hosts.img_host,
		"setup_host": config.hosts.setup_host,
		"setup_port": config.hosts.setup_port,
	}

	for source_path in template_dir.glob("*"):
		if source_path.name.startswith("."):
			continue

		if log:
			print(f" -> {source_path.name + '...':<36}", end="")
		destination_path = NGINX_PATH / source_path.name

		with open(source_path, "r", encoding="utf-8") as source_file:
			text = source_file.read()

		text = pattern.sub(lambda match: template_params[match[1]], text)

		with open(destination_path, "w", encoding="utf-8") as destination_file:
			destination_file.write(text)

		if log:
			print("done!")
