import getpass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

root_path = Path(__file__).parent

ADD_PASSWORD = False  # if you want a password for your private key enable this. ull have to change this setting in the other files tho


def main():
	key = rsa.generate_private_key(
		public_exponent=0x10001,
		key_size=2048
	)

	with open(root_path / "ca_key.pem", "wb") as private_key_file:
		private_key_file.write(key.private_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PrivateFormat.TraditionalOpenSSL,
			encryption_algorithm=serialization.BestAvailableEncryption(
				password=getpass.getpass("new RSA password: ").encode("ascii")
			) if ADD_PASSWORD else serialization.NoEncryption()
		))


if __name__ == '__main__':
	main()
