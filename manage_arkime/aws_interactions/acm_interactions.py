from datetime import timedelta
import logging

from aws_interactions.aws_client_provider import AwsClientProvider
from core.certificate_generation import SelfSignedCert

logger = logging.getLogger(__name__)

def import_self_signed_cert(cert: SelfSignedCert, aws_provider: AwsClientProvider) -> str:
    """
    Imports a self-signed cert into Amazon Certificate Manager and returns the ARN
    """

    logger.debug("Importing self-signed certificate into ACM...")

    acm_client = aws_provider.get_acm()
    import_response = acm_client.import_certificate(
        Certificate=cert.get_cert_bytes(),
        PrivateKey=cert.get_key_bytes(),
    )

    logger.debug("Self-signed certificate successfully imported")

    return import_response["CertificateArn"]

DEFAULT_ELB_DOMAIN = "*.elb.amazonaws.com"

def upload_default_elb_cert(aws_provider: AwsClientProvider) -> str:
    """
    Generates a default, self-signed certificate for use on AWS ELB's, imports it into Amazon Certificate Manager, and
    returns the ARN
    """
    logger.debug("Generating a default, self-signed certificate...")
    cert = SelfSignedCert(
        issuer_cn="Arkime",
        subject_cn=DEFAULT_ELB_DOMAIN,
        sans=[DEFAULT_ELB_DOMAIN],
        validity_duration=timedelta(days=365*10) # You probably don't care about rotation if you're using self-signed
    )
    cert.generate()
    logger.debug("Generated the certificate locally, now uploading...")

    acm_arn = import_self_signed_cert(cert, aws_provider)
    return acm_arn
