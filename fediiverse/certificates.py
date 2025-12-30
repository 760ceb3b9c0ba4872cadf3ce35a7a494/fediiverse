"""

generation code for certificates. used in first-time-config.py

"""

import datetime
from pathlib import Path
from typing import Optional

from cryptography import x509
# noinspection PyProtectedMember
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey

# just placeholders to fill the fields
ORGANIZATIONAL_UNIT_NAME = "PKI"
COUNTRY_NAME = "US"


def load_key(key_path: Path):
	"""
	loads a private key in PEM format from key_path , prompting for password if PRIVATE_KEY_HAS_PASSWORD is specified
	"""
	with open(key_path, "rb") as private_key_file:
		private_key_data = private_key_file.read()

	return serialization.load_pem_private_key(
		data=private_key_data,
		password=None
	)


def create_key(key_path: Path):
	"""
	create a private key in PEM format at key_path , prompting for password if PRIVATE_KEY_HAS_PASSWORD is specified
	"""

	key = rsa.generate_private_key(
		public_exponent=0x10001,
		key_size=2048
	)

	with open(key_path, "wb") as private_key_file:
		private_key_file.write(key.private_bytes(
			encoding=serialization.Encoding.PEM,
			format=serialization.PrivateFormat.TraditionalOpenSSL,
			encryption_algorithm=serialization.NoEncryption()
		))


def load_cert(cert_path: Path):
	"""
	loads a cert from cert_path in PEM format
	"""
	with open(cert_path, "rb") as ca_cert_file:
		return x509.load_pem_x509_certificate(ca_cert_file.read())


def create_cert(
	cert_path: Path,
	cert_der_path: Optional[Path] = None,
	*,
	public_key: RSAPublicKey,
	private_key: RSAPrivateKey,
	issuer: Optional[x509.Name],  # if None it will be self issued
	valid_length_days: int,
	common_name: str,
	organization_name: str
):
	"""
	create a cert in PEM format at cert_path
	"""
	subject = x509.Name([
		x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, ORGANIZATIONAL_UNIT_NAME),
		x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization_name),
		x509.NameAttribute(NameOID.COUNTRY_NAME, COUNTRY_NAME),
		x509.NameAttribute(NameOID.COMMON_NAME, common_name),
	])

	if issuer is None:
		# self issued CA cert.
		issuer = subject

	now = datetime.datetime.now(datetime.timezone.utc)
	cert = (
		x509.CertificateBuilder()
		.subject_name(subject)
		.issuer_name(issuer)
		.public_key(public_key)
		.serial_number(x509.random_serial_number())
		.not_valid_before(now)
		.not_valid_after(now + datetime.timedelta(days=valid_length_days))
		.add_extension(
			x509.BasicConstraints(
				ca=issuer is None,  # if self-issued this is a CA cert.
				path_length=None
			),
			critical=True
		)
		.add_extension(
			x509.SubjectKeyIdentifier.from_public_key(public_key),
			critical=False
		)
		.sign(
			private_key=private_key,
			algorithm=hashes.SHA256()
		)
	)

	with open(cert_path, "wb") as file:
		file.write(cert.public_bytes(serialization.Encoding.PEM))

	if cert_der_path:
		with open(cert_der_path, "wb") as file:
			file.write(cert.public_bytes(serialization.Encoding.DER))


def generate_certificates(
	certificates_path: Path,

	organization_name: str,
	ca_cert_common_name: str,
	ca_cert_valid_days: int,
	leaf_cert_valid_days: int,
	leaf_cert_common_name: str
):
	ca_key_path = certificates_path / "ca_key.pem"
	ca_cert_path = certificates_path / "ca_cert.pem"
	ca_cert_der_path = ca_cert_path.with_suffix(".der")
	leaf_key_path = certificates_path / "leaf_key.pem"
	leaf_cert_path = certificates_path / "leaf_cert.pem"

	if not ca_key_path.exists():
		create_key(ca_key_path)

	if not ca_cert_path.exists():
		create_cert(
			ca_cert_path,
			ca_cert_der_path,
			public_key=load_key(ca_key_path).public_key(),
			private_key=load_key(ca_key_path),
			issuer=None,
			valid_length_days=ca_cert_valid_days,
			common_name=ca_cert_common_name,
			organization_name=organization_name
		)

	if not leaf_key_path.exists():
		create_key(leaf_key_path)

	if not leaf_cert_path.exists():
		ca_cert = load_cert(ca_cert_path)
		create_cert(
			leaf_cert_path,
			private_key=load_key(ca_key_path),
			public_key=load_key(leaf_key_path).public_key(),
			issuer=ca_cert.subject,
			valid_length_days=leaf_cert_valid_days,
			common_name=leaf_cert_common_name,
			organization_name=organization_name
		)
