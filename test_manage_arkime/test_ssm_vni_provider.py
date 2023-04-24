import json
import pytest
import unittest.mock as mock

from manage_arkime.aws_interactions.ssm_operations import ParamDoesNotExist
import manage_arkime.constants as constants
import manage_arkime.vni_provider as vni


def test_WHEN_get_next_vni_called_AND_recycled_THEN_uses_recycled():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [32, 17]
    provider._get_recycled_vnis = mock_get_recycled

    mock_get_user_vnis = mock.Mock()
    provider._get_user_vnis = mock_get_user_vnis

    mock_get_current_vni = mock.Mock()
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    actual_value = provider.get_next_vni()

    # Check our results
    expected_value = 17
    assert expected_value == actual_value

def test_WHEN_get_next_vni_called_AND_next_available_THEN_returns_it():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = []
    provider._get_recycled_vnis = mock_get_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [5, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 6
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    actual_value = provider.get_next_vni()

    # Check our results
    expected_value = 7
    assert expected_value == actual_value

def test_WHEN_get_next_vni_called_AND_next_not_available_THEN_handles_gracefully():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = []
    provider._get_recycled_vnis = mock_get_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [5, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 4
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    actual_value = provider.get_next_vni()

    # Check our results
    expected_value = 6
    assert expected_value == actual_value

def test_WHEN_get_next_vni_called_AND_pool_exhausted_THEN_raises():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = []
    provider._get_recycled_vnis = mock_get_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [5, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = constants.VNI_MAX
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    with pytest.raises(vni.VniPoolExhausted):
        provider.get_next_vni()

def test_WHEN_use_next_vni_called_AND_recycled_THEN_updates():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [32, 17]
    provider._get_recycled_vnis = mock_get_recycled

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 64
    provider._get_current_autogen_vni = mock_get_current_vni

    mock_update_current_vni = mock.Mock()
    provider._update_current_autogen_vni = mock_update_current_vni

    # Run our test
    provider.use_next_vni(17)

    # Check our results
    expected_update_recycled_calls = [mock.call([32])]
    assert expected_update_recycled_calls == mock_update_recycled.call_args_list

    assert not mock_update_current_vni.called

def test_WHEN_use_next_vni_called_AND_autogen_THEN_updates():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [32, 17]
    provider._get_recycled_vnis = mock_get_recycled

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 64
    provider._get_current_autogen_vni = mock_get_current_vni

    mock_update_current_vni = mock.Mock()
    provider._update_current_autogen_vni = mock_update_current_vni

    # Run our test
    provider.use_next_vni(65)

    # Check our results
    assert not mock_update_recycled.called

    expected_update_current_calls = [mock.call(65)]
    assert expected_update_current_calls == mock_update_current_vni.call_args_list

def test_WHEN_use_next_vni_called_AND_outside_range_THEN_raises():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_update_current_vni = mock.Mock()
    provider._update_current_autogen_vni = mock_update_current_vni

    # Run our test
    with pytest.raises(vni.VniOutsideRange):
        provider.use_next_vni(constants.VNI_MIN - 1)

    with pytest.raises(vni.VniOutsideRange):
        provider.use_next_vni(constants.VNI_MAX + 1)

    # Check our results
    assert not mock_update_recycled.called
    assert not mock_update_current_vni.called

def test_WHEN_register_user_vni_called_AND_available_THEN_registered():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [5, 12]
    provider._get_recycled_vnis = mock_get_recycled

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [24, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_update_user_vni = mock.Mock()
    provider._update_user_vnis = mock_update_user_vni

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 16
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    provider.register_user_vni(18)

    # Check our results
    expected_update_user_calls = [mock.call([24, 36, 18])]
    assert expected_update_user_calls == mock_update_user_vni.call_args_list

    assert not mock_update_recycled.called

def test_WHEN_register_user_vni_called_AND_recycled_THEN_registered():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [5, 12]
    provider._get_recycled_vnis = mock_get_recycled

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [24, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_update_user_vni = mock.Mock()
    provider._update_user_vnis = mock_update_user_vni

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 16
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    provider.register_user_vni(12)

    # Check our results
    expected_update_user_calls = [mock.call([24, 36, 12])]
    assert expected_update_user_calls == mock_update_user_vni.call_args_list

    expected_update_recycled_calls = [mock.call([5])]
    assert expected_update_recycled_calls == mock_update_recycled.call_args_list

def test_WHEN_register_user_vni_called_AND_prev_autogen_THEN_raises():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [5, 12]
    provider._get_recycled_vnis = mock_get_recycled

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [24, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_update_user_vni = mock.Mock()
    provider._update_user_vnis = mock_update_user_vni

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 16
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    with pytest.raises(vni.VniAlreadyUsed):
        provider.register_user_vni(14)

    # Check our results
    assert not mock_update_user_vni.called
    assert not mock_update_recycled.called

def test_WHEN_register_user_vni_called_AND_already_registered_THEN_raises():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [5, 12]
    provider._get_recycled_vnis = mock_get_recycled

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [24, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_update_user_vni = mock.Mock()
    provider._update_user_vnis = mock_update_user_vni

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 16
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    with pytest.raises(vni.VniAlreadyUsed):
        provider.register_user_vni(24)

    # Check our results
    assert not mock_update_user_vni.called
    assert not mock_update_recycled.called

def test_WHEN_register_user_vni_called_AND_outside_range_THEN_raises():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_update_user_vni = mock.Mock()
    provider._update_user_vnis = mock_update_user_vni

    # Run our test
    with pytest.raises(vni.VniOutsideRange):
        provider.register_user_vni(constants.VNI_MIN - 1)

    with pytest.raises(vni.VniOutsideRange):
        provider.register_user_vni(constants.VNI_MAX + 1)

    # Check our results
    assert not mock_update_user_vni.called
    assert not mock_update_recycled.called

def test_WHEN_is_vni_available_called_THEN_as_expected():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [5, 12]
    provider._get_recycled_vnis = mock_get_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [24, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 16
    provider._get_current_autogen_vni = mock_get_current_vni

    # TEST: User-Specified
    actual_value = provider.is_vni_available(24)
    assert False == actual_value

    # TEST: Autogen
    actual_value = provider.is_vni_available(15)
    assert False == actual_value

    # TEST: Recycled
    actual_value = provider.is_vni_available(12)
    assert True == actual_value

    # TEST: Available
    actual_value = provider.is_vni_available(19)
    assert True == actual_value

def test_WHEN_is_vni_available_called_AND_out_of_range_THEN_raises():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    # Run our test
    with pytest.raises(vni.VniOutsideRange):
        provider.is_vni_available(constants.VNI_MIN - 1)

    with pytest.raises(vni.VniOutsideRange):
        provider.is_vni_available(constants.VNI_MAX + 1)

def test_WHEN_relinquish_vni_called_THEN_updates_state():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [5, 12]
    provider._get_recycled_vnis = mock_get_recycled

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [24, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_update_user_vni = mock.Mock()
    provider._update_user_vnis = mock_update_user_vni

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 16
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    provider.relinquish_vni(24)

    # Check our results
    expected_update_user_calls = [mock.call([36])]
    assert expected_update_user_calls == mock_update_user_vni.call_args_list

    assert not mock_update_recycled.called

def test_WHEN_relinquish_vni_called_AND_should_recycle_THEN_updates_state():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_get_recycled = mock.Mock()
    mock_get_recycled.return_value = [5, 12]
    provider._get_recycled_vnis = mock_get_recycled

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_get_user_vnis = mock.Mock()
    mock_get_user_vnis.return_value = [8, 36]
    provider._get_user_vnis = mock_get_user_vnis

    mock_update_user_vni = mock.Mock()
    provider._update_user_vnis = mock_update_user_vni

    mock_get_current_vni = mock.Mock()
    mock_get_current_vni.return_value = 16
    provider._get_current_autogen_vni = mock_get_current_vni

    # Run our test
    provider.relinquish_vni(8)

    # Check our results
    expected_update_user_calls = [mock.call([36])]
    assert expected_update_user_calls == mock_update_user_vni.call_args_list

    expected_update_recycled_calls = [mock.call([5, 12, 8])]
    assert expected_update_recycled_calls == mock_update_recycled.call_args_list

def test_WHEN_relinquish_vni_called_AND_out_of_range_THEN_raises():
    # Set up our mock
    mock_aws = mock.Mock()

    provider = vni.SsmVniProvider("cluster-1", mock_aws)

    mock_update_recycled = mock.Mock()
    provider._update_recycled_vnis = mock_update_recycled

    mock_update_user_vni = mock.Mock()
    provider._update_user_vnis = mock_update_user_vni

    # Run our test
    with pytest.raises(vni.VniOutsideRange):
        provider.relinquish_vni(constants.VNI_MIN - 1)

    with pytest.raises(vni.VniOutsideRange):
        provider.relinquish_vni(constants.VNI_MAX + 1)

    # Check our results
    assert not mock_update_user_vni.called
    assert not mock_update_recycled.called

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_update_current_autogen_vni_called_THEN_updates_it(mock_ssm):
    # Set up our mock
    mock_aws = mock.Mock()

    # Run our test
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    actual_value = provider._update_current_autogen_vni(2)

    # Check our results
    expected_value = 2
    assert expected_value == actual_value

    expected_ssm_calls = [
        mock.call(
            constants.get_vni_current_ssm_param_name("cluster-1"),
            str(2),
            mock_aws,
            description=mock.ANY,
            overwrite=True
        )
    ]
    assert expected_ssm_calls == mock_ssm.put_ssm_param.call_args_list

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_get_current_autogen_vni_called_THEN_returns_it(mock_ssm):
    # Set up our mock
    mock_ssm.get_ssm_param_value.return_value = "31"
    mock_aws = mock.Mock()

    # Run our test
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    actual_value = provider._get_current_autogen_vni()

    # Check our results
    expected_value = 31
    assert expected_value == actual_value

    expected_ssm_calls = [
        mock.call(constants.get_vni_current_ssm_param_name("cluster-1"), mock_aws)
    ]
    assert expected_ssm_calls == mock_ssm.get_ssm_param_value.call_args_list

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_get_current_autogen_vni_called_AND_not_initialized_THEN_handles_gracefully(mock_ssm):
    # Set up our mock
    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.side_effect = ParamDoesNotExist("param-1")
    mock_aws = mock.Mock()

    mock_initialize = mock.Mock()
    mock_initialize.return_value = constants.VNI_MIN - 1
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    provider._update_current_autogen_vni = mock_initialize

    # Run our test    
    actual_value = provider._get_current_autogen_vni()

    # Check our results
    expected_value = constants.VNI_MIN - 1
    assert expected_value == actual_value

    expected_initialize_calls = [
        mock.call(constants.VNI_MIN - 1)
    ]
    assert expected_initialize_calls == mock_initialize.call_args_list

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_update_recycled_vnis_called_THEN_updates_it(mock_ssm):
    # Set up our mock
    mock_aws = mock.Mock()

    # Run our test
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    actual_value = provider._update_recycled_vnis([17, 31, 82])

    # Check our results
    expected_value = [17, 31, 82]
    assert expected_value == actual_value

    expected_ssm_calls = [
        mock.call(
            constants.get_vnis_recycled_ssm_param_name("cluster-1"),
            json.dumps([17, 31, 82]),
            mock_aws,
            description=mock.ANY,
            overwrite=True
        )
    ]
    assert expected_ssm_calls == mock_ssm.put_ssm_param.call_args_list

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_get_recycled_vnis_called_THEN_returns_them(mock_ssm):
    # Set up our mock
    mock_ssm.get_ssm_param_value.return_value = json.dumps([90210, 8675309])
    mock_aws = mock.Mock()

    # Run our test
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    actual_value = provider._get_recycled_vnis()

    # Check our results
    expected_value = [90210, 8675309]
    assert expected_value == actual_value

    expected_ssm_calls = [
        mock.call(constants.get_vnis_recycled_ssm_param_name("cluster-1"), mock_aws)
    ]
    assert expected_ssm_calls == mock_ssm.get_ssm_param_value.call_args_list

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_get_recycled_vnis_called_AND_not_initialized_THEN_handles_gracefully(mock_ssm):
    # Set up our mock
    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.side_effect = ParamDoesNotExist("param-1")
    mock_aws = mock.Mock()

    mock_initialize = mock.Mock()
    mock_initialize.return_value = []
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    provider._update_recycled_vnis = mock_initialize

    # Run our test    
    actual_value = provider._get_recycled_vnis()

    # Check our results
    expected_value = []
    assert expected_value == actual_value

    expected_initialize_calls = [
        mock.call([])
    ]
    assert expected_initialize_calls == mock_initialize.call_args_list

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_update_user_vnis_called_THEN_initializes_it(mock_ssm):
    # Set up our mock
    mock_aws = mock.Mock()

    # Run our test
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    actual_value = provider._update_user_vnis([2, 19, 37])

    # Check our results
    expected_value = [2, 19, 37]
    assert expected_value == actual_value

    expected_ssm_calls = [
        mock.call(
            constants.get_vnis_user_ssm_param_name("cluster-1"),
            json.dumps([2, 19, 37]),
            mock_aws,
            description=mock.ANY,
            overwrite=True
        )
    ]
    assert expected_ssm_calls == mock_ssm.put_ssm_param.call_args_list

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_get_user_vnis_called_THEN_returns_them(mock_ssm):
    # Set up our mock
    mock_ssm.get_ssm_param_value.return_value = json.dumps([42, 16, 1337])
    mock_aws = mock.Mock()

    # Run our test
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    actual_value = provider._get_user_vnis()

    # Check our results
    expected_value = [42, 16, 1337]
    assert expected_value == actual_value

    expected_ssm_calls = [
        mock.call(constants.get_vnis_user_ssm_param_name("cluster-1"), mock_aws)
    ]
    assert expected_ssm_calls == mock_ssm.get_ssm_param_value.call_args_list

@mock.patch('manage_arkime.vni_provider.ssm_ops')
def test_WHEN_get_user_vnis_called_AND_not_initialized_THEN_handles_gracefully(mock_ssm):
    # Set up our mock
    mock_ssm.ParamDoesNotExist = ParamDoesNotExist
    mock_ssm.get_ssm_param_value.side_effect = ParamDoesNotExist("param-1")
    mock_aws = mock.Mock()

    mock_initialize = mock.Mock()
    mock_initialize.return_value = []
    provider = vni.SsmVniProvider("cluster-1", mock_aws)
    provider._update_user_vnis = mock_initialize

    # Run our test    
    actual_value = provider._get_user_vnis()

    # Check our results
    expected_value = []
    assert expected_value == actual_value

    expected_initialize_calls = [
        mock.call([])
    ]
    assert expected_initialize_calls == mock_initialize.call_args_list