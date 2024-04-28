import getpass
import datetime
from pathlib import Path
from time import sleep

from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa

root_path = Path(__file__).parent

PRIVATE_KEY_HAS_PASSWORD = False


def main():
	with open(root_path / "ca_key.pem", "rb") as private_key_file:
		private_key_data = private_key_file.read()

	key = None
	if PRIVATE_KEY_HAS_PASSWORD:
		while True:
			password = getpass.getpass("CA key RSA password: ").encode("ascii")
			if not password:
				print("password required!\n")
				sleep(1/4)
				continue

			try:
				key = serialization.load_pem_private_key(
					data=private_key_data,
					password=password
				)
				break
			except ValueError as exception:
				print(f"error: {exception}\n")
				sleep(1/4)
			finally:
				del password
	else:
		key = serialization.load_pem_private_key(
			data=private_key_data,
			password=None
		)

	print("decrypted successfully :3")

	subject = issuer = x509.Name([
		x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"PKI"),
		x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"fediiverse"),
		x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
		x509.NameAttribute(NameOID.COMMON_NAME, u"fediiverse root CA"),
	])

	now = datetime.datetime.now(datetime.timezone.utc)
	cert = (
		x509.CertificateBuilder()
		.subject_name(subject)
		.issuer_name(issuer)
		.public_key(key.public_key())
		.serial_number(x509.random_serial_number())
		.not_valid_before(now - datetime.timedelta(days=2))
		.not_valid_after(now + datetime.timedelta(days=365))
		.add_extension(
			x509.BasicConstraints(ca=True, path_length=None),
			critical=True
		)
		.add_extension(
			x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
			critical=False
		)
		.sign(
			private_key=key,
			algorithm=hashes.SHA256()
		)
	)

	with open(root_path / "ca_cert.pem", "wb") as file:
		file.write(cert.public_bytes(serialization.Encoding.PEM))

	with open(root_path / "ca_cert.der", "wb") as file:
		file.write(cert.public_bytes(serialization.Encoding.DER))


if __name__ == '__main__':
	main()
