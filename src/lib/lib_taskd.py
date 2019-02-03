from charmhelpers.core import (
    hookenv,
    host,
    templating,
    unitdata
)
from charms.reactive.helpers import any_file_changed
from charmhelpers import fetch
from pathlib import Path
import subprocess
import socket
import tempfile
import tarfile
import grp
import pwd
import os
import io


class TaskdHelper():
    def __init__(self):
        self.charm_config = hookenv.config()
        self.kv = unitdata.kv()
        self.pki_folder = "/usr/share/taskd/pki"
        self.data_folder = "/var/lib/taskd"

    def add_key(self):
        ''' An action to allow adding of users / keys'''
        return

    def del_key(self):
        ''' An action to allow removal of users / keys'''
        return

    def list_keys(self):
        ''' List all keys created for users as an action '''
        return

    @property
    def orgs(self):
        ''' Persistant dictionary of all orgs and user data '''
        orgs = self.kv.get('orgs')
        if orgs is None:
            orgs = {}
            self.kv.set('orgs', orgs)
            self.kv.flush()
        return orgs

    @orgs.setter
    def orgs(self, orgs):
        self.kv.set('orgs', orgs)
        self.kv.flush()

    def add_org(self, org_name):
        ''' Add an organization '''
        orgs = self.orgs
        cmd = ['taskd',
               'add',
               'org',
               org_name,
               '--data',
               self.data_folder,
               ]
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            hookenv.log("Failed to create org: {}".format(e.output.decode()), 'ERROR')
            return e.output.decode()
        orgs[org_name] = {}
        self.orgs = orgs
        hookenv.log("Create org: {}".format(org_name), 'INFO')

    def add_user(self, org_name, user_name):
        ''' Add a user to an organization '''
        orgs = self.orgs
        if orgs.get(org_name) is None:
            return "Org does not exist, create it first"
        if orgs.get(org_name).get(user_name):
            return "User already exists"
        cmd = ['taskd',
               'add',
               'user',
               org_name,
               user_name,
               '--data',
               self.data_folder,
               ]
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            hookenv.log("Failed to create user: {}".format(e.output.decode()), 'ERROR')
            return e.output.decode()
        key = result.decode().split('\n')[0].split(':')[1].strip()
        orgs[org_name][user_name] = {}
        orgs[org_name][user_name]['key'] = key
        cert_name = '{}_{}'.format(org_name,
                                   user_name.replace(' ', '_')
                                   )
        err = self.create_cert(cert_name)
        if err:
            return err
        orgs[org_name][user_name]['cert_name'] = cert_name
        self.orgs = orgs
        self.fix_permissions()

    def remove_user(self, org_name, user_name):
        ''' Remove a user '''
        orgs = self.orgs
        if not orgs.get(org_name).get(user_name):
            return "User does not exists"
        key = orgs[org_name][user_name]['key']
        cmd = ['taskd',
               'remove',
               'user',
               org_name,
               key,
               '--data',
               self.data_folder,
               ]
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            hookenv.log("Failed to remove user: {}".format(e.output.decode()), 'ERROR')
            return e.output.decode()
        cert_name = orgs[org_name][user_name]['cert_name']
        for path in Path(self.pki_folder).glob("{}.*".format(cert_name)):
            path.unlink()
        del orgs[org_name][user_name]
        self.orgs = orgs

    def remove_org(self, org_name):
        ''' Remove an org and all users in it '''
        orgs = self.orgs
        if not orgs.get(org_name):
            return "Org does not exists"
        for user in orgs[org_name]:
            self.remove_user(org_name, user)
        cmd = ['taskd',
               'remove',
               'org',
               org_name,
               '--data',
               self.data_folder,
               ]
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            hookenv.log("Failed to remove org: {}".format(e.output.decode()), 'ERROR')
            return e.output.decode()
        del orgs[org_name]
        self.orgs = orgs

    def create_cert(self, user_name):
        ''' Generate a cert with the given user name '''
        os.chdir(self.pki_folder)
        cmd = ['./generate.client',
               user_name]
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            hookenv.log("Failed to generate cert: {}".format(e.output.decode()), 'ERROR')
            return e.output.decode()
        self.fix_permissions()

    def get_user_config(self, org_name, user_name):
        ''' retreive the congiruation for a user '''
        orgs = self.orgs
        if not orgs.get(org_name):
            return 'Org does not exist'
        if not orgs.get(org_name).get(user_name):
            return "User does not exists"
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tar_name = tmp_file.name + '.tgz'
        tar_file = tarfile.open(tar_name,
                                mode='w:gz',
                                )
        pki = Path(self.pki_folder)
        ca_path = pki / Path('ca.cert.pem')
        tar_file.addfile(tar_file.gettarinfo(name=ca_path,
                                             arcname="ca.cert.pem"),
                         open(ca_path, 'rb')
                         )
        cert_file = orgs[org_name][user_name]['cert_name'] + ".cert.pem"
        cert_path = pki / Path(cert_file)
        tar_file.addfile(tar_file.gettarinfo(name=cert_path,
                                             arcname=cert_file),
                         open(cert_path, 'rb')
                         )
        key_file = orgs[org_name][user_name]['cert_name'] + ".key.pem"
        key_path = pki / Path(key_file)
        tar_file.addfile(tar_file.gettarinfo(name=key_path,
                                             arcname=key_file),
                         open(key_path, 'rb')
                         )

        context = {'org_name': org_name,
                   'user_name': user_name,
                   'user_key': orgs[org_name][user_name]['key'],
                   'cert_name': cert_file,
                   'key_name': key_file,
                   'task_port': self.charm_config['port'],
                   'task_server': socket.getfqdn(),
                   }

        config_script = templating.render('task.rc.j2',
                                          None,
                                          context,
                                          )
        config_info = tarfile.TarInfo(name='setup.sh')
        config_info.size = len(config_script)
        config_info.mode = 0o0755
        tar_file.addfile(config_info,
                         io.BytesIO(config_script.encode('utf8')),
                         )
        tar_file.close()
        return tar_name

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
