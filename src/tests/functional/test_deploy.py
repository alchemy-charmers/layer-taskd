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
