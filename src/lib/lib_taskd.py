from charmhelpers.core import (
    hookenv,
    host,
    templating,
    unitdata
)
from charms.reactive.helpers import any_file_changed
from charmhelpers import fetch
import subprocess
import socket
import grp
import pwd
import os


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

    def fix_permissions(self):
        ''' Fix permissions '''
        ''' Taskd doesn't run as root '''
        for path in [
                '/var/lib/taskd',
                '/usr/share/taskd']:
            uid = pwd.getpwnam('Debian-taskd').pw_uid
            gid = grp.getgrnam('Debian-taskd').gr_gid
            for root, dirnames, filenames in os.walk(path):
                os.chown(root, uid, gid)
                hookenv.log("Fixing data dir permissions: {}".format(
                    root), 'DEBUG')
                for dirname in dirnames:
                    os.chown(os.path.join(root, dirname), uid, gid)
                    hookenv.log("Fixing dir permissions: {}".format(
                        dirname), 'DEBUG')
                for filename in filenames:
                    os.chown(os.path.join(root, filename), uid, gid)
                    hookenv.log("Fixing file permissions: {}".format(
                        filename), 'DEBUG')

    def restart(self):
        host.service('restart', 'taskd')

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
        restart = False

        server = "{}:{}".format(
            self.charm_config['listen'],
            self.charm_config['port'])

        hookenv.log("Configuring taskd server {}".format(
                    server), 'DEBUG')

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
            restart = True

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
            restart = True

        fullport = "{}/tcp".format(
            self.charm_config['port'])

        for port in hookenv.opened_ports():
            if not fullport == port:
                cport, cproto = port.split('/')
                hookenv.close_port(cport, cproto)

        if fullport not in hookenv.opened_ports():
            hookenv.open_port(
                self.charm_config['port'],
                'tcp')

        self.fix_permissions()
        self.start_enable()

        if restart:
            self.restart()

    def install(self):
        fetch.apt_install('taskd', fatal=True)
        self.configure()
        return True
