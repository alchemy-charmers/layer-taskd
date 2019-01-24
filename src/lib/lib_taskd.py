from charmhelpers.core import hookenv, host, templating, unitdata
from charms.reactive.helpers import any_file_changed
from charmhelpers import fetch
import subprocess
import socket


class TaskdHelper():
    def __init__(self):
        self.charm_config = hookenv.config()
        self.kv = unitdata.kv()

    def add_key(self):
        ''' An action to allow adding of users / keys'''
        return

    def del_key(self):
        ''' An action to allow removal of users / keys'''
        return

    def list_keys(self):
        ''' List all keys created for users as an action '''
        return

    def start_enable(self):
        host.service('enable', 'taskd')
        host.service('start', 'taskd')

    def configure_proxy(self, proxy):
        proxy_config = [
            {
                'mode': 'tcp',
                'external_port': self.charm_config['port'],
                'internal_host': socket.getfqdn(),
                'internal_port': self.charm_config['port']
            }
        ]
        proxy.configure(proxy_config)

    def configure(self):
        server = "{}:{}".format(
            self.charm_config['listen'],
            self.charm_config['port'])
        templating.render('config.j2',
                          '/var/lib/taskd/config',
                          {
                              'server': server
                          })

        if any_file_changed(['/var/lib/taskd/config']):
            p = subprocess.Popen(['/usr/bin/taskd',
                                  'init',
                                  '--data',
                                  '/var/lib/taskd'])
            p.wait()
            host.service('restart', 'taskd')

        if self.charm_config['tls_cn']:
            cn = self.charm_config['tls_cn']
        else:
            cn = socket.getfqdn()

        templating.render('vars.j2',
                          '/usr/share/taskd/pki/vars',
                          {
                              'expiry':
                              self.charm_config['tls_expiry'],
                              'org':
                              self.charm_config['tls_org'],
                              'cn': cn,
                              'country':
                              self.charm_config['tls_country'],
                              'state':
                              self.charm_config['tls_state'],
                              'locality':
                              self.charm_config['tls_locality']
                          })

        if any_file_changed(['/usr/share/taskd/pki/vars']):
            p = subprocess.Popen(['/usr/share/taskd/pki/generate'],
                                 cwd='/usr/share/taskd/pki')
            p.wait()
            host.service('restart', 'taskd')

    def install(self):
        fetch.apt_install('taskd', fatal=True)
        return True
