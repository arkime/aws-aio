import pytest
import unittest.mock as mock

from botocore.exceptions import ClientError

from manage_arkime.aws_interactions.get_ssm_parameter import get_ssm_param, ParamDoesNotExist


def test_WHEN_get_ssm_param_called_AND_exists_THEN_destroys_it():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "param"}}

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    actual_value = get_ssm_param("my-param", mock_aws_provider)

    # Check our results
    expected_get_calls = [
        mock.call(Name="my-param")
    ]
    assert expected_get_calls == mock_ssm_client.get_parameter.call_args_list

    expected_value = "param"
    assert expected_value == actual_value

def test_WHEN_get_ssm_param_called_AND_doesnt_exist_THEN_raises():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_ssm_client.get_parameter.side_effect = [
        ClientError(error_response={"Error": {"Code": "ResourceNotFoundException"}}, operation_name="") # Already gone
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    with pytest.raises(ParamDoesNotExist):
        get_ssm_param("my-param", mock_aws_provider)
