from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import logging
from typing import List

logger = logging.getLogger(__name__)

RSA_PUBLIC_EXPONENT = 65537 # Industry standard value for RSA key gen

class CertNotYetGenerated(Exception):
    def __init__(self):
        super().__init__("The certificate for this object has not yet been generated")

class KeyNotYetGenerated(Exception):
    def __init__(self):
        super().__init__("The private key for this object has not yet been generated")

class SelfSignedCert:
    def __init__(self, issuer_cn: str, subject_cn: str, sans: List[str], validity_duration: datetime.timedelta, key_size: int = 2048):
        """
        issuer_cn: Used for Issuer Common Name
        subject_cn: Used for the Subject Common Name
        sans: List of domains for the Subject Alternative Name field
        validity_duration: Time period the cert will be valid for
        key_size: RSA key size for the certificate
        """
        # Input fields
        self._issuer_cn = issuer_cn
        self._subject_cn = subject_cn
        self._sans = sans
        self._validity_duration = validity_duration
        self._key_size = key_size

        # Internal state
        self._public_exponent: int = RSA_PUBLIC_EXPONENT
        self._private_key = None
        self._certificate = None

    def generate(self):
        logger.info("Generating self-signed certificate...")
        if self._private_key or self._certificate:
            logger.warning("Certificate already generated for this instance; aborting")
            return

        logger.debug("Generating RSA private key...")
        self._private_key = rsa.generate_private_key(
            public_exponent=self._public_exponent,
            key_size=self._key_size,
        )
        logger.debug("RSA private key generated")

        logger.debug("Preparing certificate for signing...")
        issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, self._issuer_cn)])
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, self._subject_cn)])

        cert_builder = x509.CertificateBuilder()
        cert_builder = cert_builder.subject_name(subject)
        cert_builder = cert_builder.issuer_name(issuer)
        cert_builder = cert_builder.public_key(self._private_key.public_key())
        cert_builder = cert_builder.serial_number(x509.random_serial_number())
        cert_builder = cert_builder.not_valid_before(datetime.datetime.utcnow())
        cert_builder = cert_builder.not_valid_after(
            datetime.datetime.utcnow() + self._validity_duration
        )

        san_objects = [x509.DNSName(domain) for domain in self._sans]
        san = x509.SubjectAlternativeName(san_objects)
        cert_builder = cert_builder.add_extension(san, critical=False)

        logger.debug("Signing the certificate...")
        self._certificate = cert_builder.sign(self._private_key, hashes.SHA256())
        logger.info("Certificate generated")

    def get_cert_bytes(self) -> bytes:
        """
        Returns the certificate as bytes in the PEM format
        """
        if not self._certificate:
            logger.error("Certificate not yet generated")
            raise CertNotYetGenerated()
        
        return self._certificate.public_bytes(serialization.Encoding.PEM)
    
    def get_key_bytes(self) -> bytes:
        """
        Returns the UNENCRYPTED private key as bytes in the PEM format
        """
        if not self._private_key:
            logger.error("Private key not yet generated")
            raise KeyNotYetGenerated()
        
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )