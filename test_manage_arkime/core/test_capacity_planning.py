import pytest

import core.capacity_planning as cap


def test_WHEN_get_capture_node_capacity_plan_called_THEN_as_expected():
    # TEST 1: No expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(None)
    expected_value = cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1)

    assert expected_value == actual_value
    
    # TEST 2: Small expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(0.001)
    expected_value = cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 1, 2, 1)

    assert expected_value == actual_value

    # TEST 3: Mid-range expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(20)
    expected_value = cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 10, 13, 1)

    assert expected_value == actual_value

    # TEST 4: Max expected traffic number

    actual_value = cap.get_capture_node_capacity_plan(cap.MAX_TRAFFIC)
    expected_value = cap.CaptureNodesPlan(cap.INSTANCE_TYPE_CAPTURE_NODE, 50, 63, 1)

    assert expected_value == actual_value

    # TEST 5: Excessive expected traffic number

    with pytest.raises(cap.TooMuchTraffic):
        cap.get_capture_node_capacity_plan(cap.MAX_TRAFFIC + 10)


def test_WHEN_get_ecs_sys_resource_plan_called_THEN_as_expected():
    # TEST 1: Get an m5.xlarge instance
    actual_value = cap.get_ecs_sys_resource_plan(cap.INSTANCE_TYPE_CAPTURE_NODE)
    expected_value = cap.EcsSysResourcePlan(3584, 15360)

    assert expected_value == actual_value

    # TEST 2: Get an unknown instance type
    with pytest.raises(cap.UnknownInstanceType):
        cap.get_ecs_sys_resource_plan("unknown")