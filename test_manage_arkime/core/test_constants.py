import core.constants as constants


def test_WHEN_is_valid_cluster_name_called_THEN_as_expected():
    # TEST: Simple string should pass
    actual_value = constants.is_valid_cluster_name("MyCluster01")
    assert True == actual_value

    # TEST: String with hyphens, underscores should pass
    actual_value = constants.is_valid_cluster_name("My-Cluster_01")
    assert True == actual_value

    # TEST: Empty string should fail
    actual_value = constants.is_valid_cluster_name("")
    assert False == actual_value

    # TEST: String with space should fail
    actual_value = constants.is_valid_cluster_name("MyCluster 01")
    assert False == actual_value

    # TEST: String with other character should fail
    actual_value = constants.is_valid_cluster_name("My*Cluster01")
    assert False == actual_value