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
ADD_PASSWORD = False  # if you want a password for your leaf cert enable this. youll have to type it in every time you start nginx


def main():
	with open(root_path / "ca_key.pem", "rb") as ca_key_file:
		ca_key_data = ca_key_file.read()

	ca_key = None
	if PRIVATE_KEY_HAS_PASSWORD:
		while True:
			ca_key_password = getpass.getpass("CA key RSA pass please: ").encode("ascii")
			if not ca_key_password:
				print("password required!\n")
				sleep(1/4)
				continue

			try:
				ca_key = serialization.load_pem_private_key(
					data=ca_key_data,
					password=ca_key_password
				)
				break
			except ValueError as exception:
				print(f"error: {exception}\n")
				sleep(1/4)
			finally:
				del ca_key_password
	else:
		ca_key = serialization.load_pem_private_key(
			data=ca_key_data,
			password=None
		)

	print("decrypted successfully :3")

	with open(root_path / "ca_cert.pem", "rb") as ca_cert_file:
		ca_cert = x509.load_pem_x509_certificate(ca_cert_file.read())

	leaf_key = rsa.generate_private_key(
		public_exponent=0x10001,
		key_size=2048
	)

	with open(root_path / "leaf_key.pem", "wb") as leaf_key_file:
		leaf_key_file.write(leaf_key.private_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PrivateFormat.TraditionalOpenSSL,
			encryption_algorithm=serialization.BestAvailableEncryption(
				password=getpass.getpass("new RSA password: ").encode("ascii")
			) if ADD_PASSWORD else serialization.NoEncryption()
		))

	subject = x509.Name([
		x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"PKI"),
		x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"fediiverse"),
		x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
		x509.NameAttribute(NameOID.COMMON_NAME, u"*.fediiverse.local")
	])

	now = datetime.datetime.now(datetime.timezone.utc)
	cert = (
		x509.CertificateBuilder()
		.subject_name(subject)
		.issuer_name(ca_cert.subject)  # IMPORTANT!!!!
		.public_key(leaf_key.public_key())  # IMPORTANT!!!
		.serial_number(x509.random_serial_number())
		.not_valid_before(now - datetime.timedelta(days=2))
		.not_valid_after(now + datetime.timedelta(days=365))
		.add_extension(
			x509.BasicConstraints(ca=False, path_length=None),
			critical=True,
		)
		.add_extension(
			x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()),
			critical=False
		)
		.add_extension(
			x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(ca_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier).value),
			critical=False
		)
		.add_extension(
			x509.SubjectAlternativeName([
				x509.DNSName("*.fediiverse.local")
			]),
			critical=False
		)
		.sign(
			private_key=ca_key,
			algorithm=hashes.SHA256()
		)
	)

	with open(root_path / "leaf_cert.pem", "wb") as file:
		file.write(cert.public_bytes(serialization.Encoding.PEM))

	with open(root_path / "leaf_cert.der", "wb") as file:
		file.write(cert.public_bytes(serialization.Encoding.DER))


if __name__ == '__main__':
	main()
