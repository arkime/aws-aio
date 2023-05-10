from datetime import timedelta
import unittest.mock as mock

from aws_interactions.acm_interactions import import_self_signed_cert, upload_default_elb_cert, DEFAULT_ELB_DOMAIN


def test_WHEN_import_self_signed_cert_called_THEN_imports():
    # Set up our mock
    mock_cert = mock.Mock()
    mock_cert.get_cert_bytes.return_value = b'cert'
    mock_cert.get_key_bytes.return_value = b'key'

    mock_client = mock.Mock()
    mock_client.import_certificate.return_value = {
        "CertificateArn": "arn"
    }
    mock_provider = mock.Mock()
    mock_provider.get_acm.return_value = mock_client

    # Run our test
    actual_value = import_self_signed_cert(mock_cert, mock_provider)

    # Check our results
    assert "arn" == actual_value

    expected_import_calls = [
        mock.call(Certificate=b'cert', PrivateKey=b'key')
    ]
    assert expected_import_calls == mock_client.import_certificate.call_args_list

@mock.patch("aws_interactions.acm_interactions.import_self_signed_cert")
@mock.patch("aws_interactions.acm_interactions.SelfSignedCert")
def test_WHEN_upload_default_elb_cert_called_THEN_as_expected(mock_cert_cls, mock_import):
    # Set up our mock
    mock_cert = mock.Mock()
    mock_cert_cls.return_value = mock_cert

    mock_import.return_value = "arn"

    mock_provider = mock.Mock()

    # Run our test
    actual_value = upload_default_elb_cert(mock_provider)

    # Check our results
    assert "arn" == actual_value

    expected_cert_gen_calls = [
        mock.call(
            issuer_cn="Arkime",
            subject_cn=DEFAULT_ELB_DOMAIN,
            sans=[DEFAULT_ELB_DOMAIN],
            validity_duration=timedelta(days=365*10)
        )
    ]
    assert expected_cert_gen_calls == mock_cert_cls.call_args_list
    
    assert mock_cert.generate.called

    expected_import_calls = [
        mock.call(mock_cert, mock_provider)
    ]
    assert expected_import_calls == mock_import.call_args_list

