import json
import pytest
import unittest.mock as mock

from botocore.exceptions import ClientError

import aws_interactions.ssm_operations as ssm


def test_WHEN_get_ssm_param_value_called_AND_exists_THEN_gets_it():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "param"}}

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    actual_value = ssm.get_ssm_param_value("my-param", mock_aws_provider)

    # Check our results
    expected_get_calls = [
        mock.call(Name="my-param")
    ]
    assert expected_get_calls == mock_ssm_client.get_parameter.call_args_list

    expected_value = "param"
    assert expected_value == actual_value

def test_WHEN_get_ssm_param_value_called_AND_doesnt_exist_THEN_raises():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_ssm_client.get_parameter.side_effect = [
        ClientError(error_response={"Error": {"Code": "ParameterNotFound"}}, operation_name="")
    ]

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    with pytest.raises(ssm.ParamDoesNotExist):
        ssm.get_ssm_param_value("my-param", mock_aws_provider)

def test_WHEN_get_ssm_param_json_value_called_THEN_gets_it():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_ssm_client.get_parameter.return_value = {
        "Parameter": {
            "Value": json.dumps({"key-1": "value-1"})
        }
    }

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    actual_value = ssm.get_ssm_param_json_value("my-param", "key-1", mock_aws_provider)

    # Check our results
    expected_get_calls = [
        mock.call(Name="my-param")
    ]
    assert expected_get_calls == mock_ssm_client.get_parameter.call_args_list

    expected_value = "value-1"
    assert expected_value == actual_value

def test_WHEN_get_ssm_params_by_path_called_AND_exists_THEN_gets_them():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_ssm_client.get_parameters_by_path.side_effect = [
        {"Parameters": [{"k1": "v1"}, {"k2": "v2"}], "NextToken": "1234"},
        {"Parameters": [{"k3": "v3"}]},
    ]    

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    actual_value = ssm.get_ssm_params_by_path("/the/path", mock_aws_provider)

    # Check our results
    expected_get_calls = [
        mock.call(Path="/the/path"),
        mock.call(Path="/the/path", NextToken="1234"),
    ]
    assert expected_get_calls == mock_ssm_client.get_parameters_by_path.call_args_list

    expected_value = [
        {"k1": "v1"}, {"k2": "v2"}, {"k3": "v3"}
    ]
    assert expected_value == actual_value

def test_WHEN_get_ssm_params_by_path_called_AND_doesnt_exists_THEN_empty_result():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_ssm_client.get_parameters_by_path.return_value = []    

    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    actual_value = ssm.get_ssm_params_by_path("/the/path", mock_aws_provider)

    # Check our results
    expected_get_calls = [
        mock.call(Path="/the/path")
    ]
    assert expected_get_calls == mock_ssm_client.get_parameters_by_path.call_args_list

    expected_value = []
    assert expected_value == actual_value

@mock.patch("aws_interactions.ssm_operations.get_ssm_params_by_path")
def test_WHEN_get_ssm_names_by_path_called_THEN_gets_them(mock_get_params):
    # Set up our mock
    mock_get_params.return_value = [
        {"Name": "/the/path/name1", "Value": "v1"},
        {"Name": "/the/path/name2", "Value": "v2"},
        {"Name": "/the/path/name3", "Value": "v3"},
    ]

    mock_aws_provider = mock.Mock()

    # Run our test
    actual_value = ssm.get_ssm_names_by_path("/the/path", mock_aws_provider)

    # Check our results
    expected_get_calls = [
        mock.call("/the/path", mock_aws_provider)
    ]
    assert expected_get_calls == mock_get_params.call_args_list

    expected_value = ["name1", "name2", "name3"]
    assert expected_value == actual_value

def test_WHEN_put_ssm_param_called_THEN_puts_it():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    ssm.put_ssm_param("my-param", "param-value", mock_aws_provider, description="param-desc", pattern=".*", overwrite=True)

    # Check our results
    expected_put_calls = [
        mock.call(
            Name="my-param",
            Description="param-desc",
            Value="param-value",
            Type="String",
            AllowedPattern=".*",
            Tier='Standard',
            Overwrite=True
        )
    ]
    assert expected_put_calls == mock_ssm_client.put_parameter.call_args_list

def test_WHEN_delete_ssm_param_called_THEN_deletes_it():
    # Set up our mock
    mock_ssm_client = mock.Mock()
    mock_aws_provider = mock.Mock()
    mock_aws_provider.get_ssm.return_value = mock_ssm_client    

    # Run our test
    ssm.delete_ssm_param("my-param", mock_aws_provider)

    # Check our results
    expected_delete_calls = [
        mock.call(Name="my-param")
    ]
    assert expected_delete_calls == mock_ssm_client.delete_parameter.call_args_list
