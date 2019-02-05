#!/usr/bin/python3


def test_pytest():
    assert True


def test_taskd(taskd):
    ''' See if the helper fixture works to load charm configs '''
    assert isinstance(taskd.charm_config, dict)

# Include tests for functions in lib_taskd
