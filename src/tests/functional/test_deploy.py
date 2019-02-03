import pytest
import os
import yaml
from juju.model import Model

# Treat tests as coroutines
pytestmark = pytest.mark.asyncio

# Load charm metadata
metadata = yaml.load(open("./metadata.yaml"))
juju_repository = os.getenv('JUJU_REPOSITORY',
                            '.').rstrip('/')
charmname = metadata['name']
series = ['xenial', 'bionic']


@pytest.fixture
async def model():
    model = Model()
    await model.connect_current()
    yield model
    await model.disconnect()


@pytest.fixture
async def units(model):
    units = []
    for entry in series:
        app = model.applications['taskd-{}'.format(entry)]
        units.extend(app.units)
    return units


@pytest.fixture
async def apps(model):
    apps = []
    for entry in series:
        app = model.applications['taskd-{}'.format(entry)]
        apps.append(app)
    return apps


@pytest.mark.parametrize('series', series)
async def test_taskd_deploy(model, series):
    await model.deploy('{}/builds/taskd'.format(juju_repository),
                       series=series,
                       application_name='taskd-{}'.format(series))
    assert True


async def test_taskd_status(apps, model):
    for app in apps:
        await model.block_until(lambda: app.status == 'active')
    assert True


async def test_add_org(units):
    for unit in units:
        # Add a new org should pass
        action = await unit.run_action('add-org', org='test')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'completed'

        # Add an existing org should fail
        action = await unit.run_action('add-org', org='test')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'failed'


async def test_add_user(units):
    for unit in units:
        # Add user to deafult org
        action = await unit.run_action('add-user', user='test-user')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'completed'

        # Add user to test org
        action = await unit.run_action('add-user', org='test', user='test-user')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'completed'

        # Fail to add a user the 2nd time
        action = await unit.run_action('add-user', org='test', user='test-user')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'failed'


async def test_remove_user(units):
    for unit in units:
        # Remove test-user from default
        action = await unit.run_action('remove-user', user='test-user')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'completed'

        # Remove test-user from test org
        action = await unit.run_action('remove-user', org='test', user='test-user')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'completed'

        # 2nd remove should fail
        action = await unit.run_action('remove-user', user='test-user')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'failed'


async def test_remove_org(units):
    for unit in units:
        # Remove test org
        action = await unit.run_action('remove-org', org='test')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'completed'

        # 2nd remove should fail
        action = await unit.run_action('remove-org', org='test')
        action = await action.wait()
        print(unit)
        print(action)
        assert action.status == 'failed'
