from datetime import datetime, timedelta
import pytest
import unittest.mock as mock

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization

from core.certificate_generation import SelfSignedCert, RSA_PUBLIC_EXPONENT, CertNotYetGenerated, KeyNotYetGenerated


@mock.patch("core.certificate_generation.datetime")
@mock.patch("core.certificate_generation.x509.CertificateBuilder")
@mock.patch("core.certificate_generation.rsa")
def test_WHEN_generate_called_THEN_generates_certificate(mock_rsa, mock_builder_cls, mock_datetime):
    # Set up our mock
    mock_key = mock.Mock()
    mock_rsa.generate_private_key.return_value = mock_key

    mock_cert = mock.Mock()
    mock_builder = mock.Mock()
    mock_builder.subject_name.return_value = mock_builder
    mock_builder.issuer_name.return_value = mock_builder
    mock_builder.public_key.return_value = mock_builder
    mock_builder.serial_number.return_value = mock_builder
    mock_builder.not_valid_before.return_value = mock_builder
    mock_builder.not_valid_after.return_value = mock_builder
    mock_builder.add_extension.return_value = mock_builder
    mock_builder.sign.return_value = mock_cert
    mock_builder_cls.return_value = mock_builder

    now = datetime.utcnow()
    mock_datetime.datetime.utcnow.return_value = now

    # Run our test
    test_cert = SelfSignedCert("issuer", "subject", ["san1", "san2"], timedelta(days=365), key_size=4096)
    test_cert.generate()

    # Check our results
    expected_rsa_gen_calls = [
        mock.call(public_exponent=RSA_PUBLIC_EXPONENT, key_size=4096)
    ]
    assert expected_rsa_gen_calls == mock_rsa.generate_private_key.call_args_list

    assert mock_key == test_cert._private_key
    assert mock_cert == test_cert._certificate

    # Check the cert was created in the way we expected
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "subject")])
    assert [mock.call(subject)] == mock_builder.subject_name.call_args_list

    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "issuer")])
    assert [mock.call(issuer)] == mock_builder.issuer_name.call_args_list

    assert [mock.call(mock_key.public_key())] == mock_builder.public_key.call_args_list

    assert [mock.call(mock.ANY)] == mock_builder.serial_number.call_args_list

    assert [mock.call(now)] == mock_builder.not_valid_before.call_args_list

    assert [mock.call(now + timedelta(days=365))] == mock_builder.not_valid_after.call_args_list

    san = x509.SubjectAlternativeName([
        x509.DNSName("san1"),
        x509.DNSName("san2"),
    ])
    assert [mock.call(san, critical=False)] == mock_builder.add_extension.call_args_list

@mock.patch("core.certificate_generation.x509.CertificateBuilder")
@mock.patch("core.certificate_generation.rsa")
def test_WHEN_generate_called_AND_already_gen_THEN_aborts(mock_rsa, mock_builder_cls):
    # Run our test
    test_cert = SelfSignedCert("issuer", "subject", ["san1", "san2"], timedelta(days=365), key_size=4096)
    test_cert._certificate = "blah"
    test_cert._private_key = "blah"
    test_cert.generate()

    # Check our results
    assert not mock_rsa.generate_private_key.called
    assert not mock_builder_cls.called
    
def test_WHEN_get_cert_bytes_THEN_as_expected():
    # TEST 1: Has been generated
    test_cert_1 = SelfSignedCert("issuer", "subject", ["san1", "san2"], timedelta(days=365), key_size=4096)
    mock_cert_1 = mock.Mock()
    mock_cert_1.public_bytes.return_value = b"public"
    test_cert_1._certificate = mock_cert_1

    assert b"public" == test_cert_1.get_cert_bytes()
    assert [mock.call(serialization.Encoding.PEM)] == mock_cert_1.public_bytes.call_args_list


    # TEST 2: Has not been generated
    test_cert_2 = SelfSignedCert("issuer", "subject", ["san1", "san2"], timedelta(days=365), key_size=4096)
    test_cert_2._certificate = None

    with pytest.raises(CertNotYetGenerated):
        test_cert_2.get_cert_bytes()
    
@mock.patch("core.certificate_generation.serialization.NoEncryption")
def test_WHEN_get_key_bytes_THEN_as_expected(mock_no_encryption_cls):
    # TEST 1: Has been generated
    mock_no_encryption = mock.Mock()
    mock_no_encryption_cls.return_value = mock_no_encryption

    test_cert_1 = SelfSignedCert("issuer", "subject", ["san1", "san2"], timedelta(days=365), key_size=4096)
    mock_key_1 = mock.Mock()
    mock_key_1.private_bytes.return_value = b"private"
    test_cert_1._private_key = mock_key_1

    assert b"private" == test_cert_1.get_key_bytes()
    assert [mock.call(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=mock_no_encryption)
        ] == mock_key_1.private_bytes.call_args_list
    

    # TEST 2: Has not been generated
    test_cert_2 = SelfSignedCert("issuer", "subject", ["san1", "san2"], timedelta(days=365), key_size=4096)
    test_cert_2._private_key = None

    with pytest.raises(KeyNotYetGenerated):
        test_cert_2.get_key_bytes()