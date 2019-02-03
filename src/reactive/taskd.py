from lib_taskd import TaskdHelper
from charmhelpers.core import hookenv
from charms.reactive import (
    endpoint_from_name,
    set_flag,
    clear_flag,
    when_not,
    when_all,
    when
)

taskd = TaskdHelper()
HEALTHY = 'taskd installed and configured'


@when_not('taskd.installed')
def install_taskd():
    hookenv.status_set('maintenance', 'Installing taskd')
    taskd.install()
    hookenv.status_set('active', 'taskd installed')
    set_flag('taskd.installed')


@when_all('config.changed', 'taskd.installed')
def configure_taskd():
    hookenv.status_set('maintenance', 'Configuring taskd')
    taskd.configure()
    taskd.add_org('default')
    hookenv.status_set('active', HEALTHY)
    set_flag('taskd.configured')


@when('reverseproxy.departed')
def remove_proxy():
    hookenv.status_set(
        'maintenance',
        'Removing reverse proxy relation')
    hookenv.log("Removing config for: {}".format(
        hookenv.remote_unit()))

    hookenv.status_set('active', HEALTHY)
    clear_flag('reverseproxy.configured')


@when('reverseproxy.ready')
@when_not('reverseproxy.configured')
def configure_proxy():
    hookenv.status_set(
        'maintenance',
        'Applying reverse proxy configuration')
    hookenv.log("Configuring reverse proxy via: {}".format(
        hookenv.remote_unit()))

    interface = endpoint_from_name('reverseproxy')
    taskd.configure_proxy(interface)

    hookenv.status_set('active', HEALTHY)
    set_flag('reverseproxy.configured')
