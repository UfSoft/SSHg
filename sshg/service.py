# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.service
    ~~~~~~~~~~~~

    This module is responsible for console options parsing and services
    starting.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import sys
from ConfigParser import SafeConfigParser
import getpass
from os import makedirs
from os.path import abspath, basename, dirname, expanduser, isdir, isfile, join
from types import ModuleType

from nevow import appserver
from twisted.application import internet
from twisted.application.service import (IServiceMaker, Application,
                                         IServiceCollection)
from twisted.plugin import IPlugin
from twisted.python import usage
from zope.interface import implements

from pyamf import register_class

from sshg import __version__, __summary__, application, config
from sshg.checkers import MercurialPublicKeysDB
from sshg.database import (create_engine, metadata, session, User, PublicKey,
                           Repository)
from sshg.factories import MercurialReposFactory, ConfigurationFactory
from sshg.portals import MercurialRepositoriesPortal
from sshg.realms import MercurialRepositoriesRealm
from sshg.web.site import SSHgWebConfigRoot # After templates are defined

class PasswordsDoNotMatch(Exception):
    """Simple exception to catch non-matching passwords"""

def ask_password(ask_pass_text=None, calledback=None):
    if calledback is not None:
        # This is called automatically if it's OpenSSL asking for it
        return getpass.getpass("Please specify the password for the key: ")

    # It's not a password being requested, it's a password to define
    passwd = getpass.getpass(ask_pass_text or
                             "Define a password for the new private key "
                             "(leave empty for none): ")
    if not passwd:
        return None
    verify_password = getpass.getpass("Verify Password: ")
    if passwd != verify_password:
        print "Passwords do not match!"
        raise PasswordsDoNotMatch
    return passwd

class BaseOptions(usage.Options):
    def opt_version(self):
        """Show version"""
        print "%s - %s" % (basename(sys.argv[0]), __version__)
    opt_v = opt_version

    def opt_help(self):
        """Show this help message"""
        super(BaseOptions, self).opt_help()
    opt_h = opt_help

class SetupOptions(BaseOptions):
    longdesc = "Configure SSHg"

    def getService(self):
        if not isfile(config.private_key):
            print "Generating the SSH Private Key"
            from OpenSSL import crypto
            privateKey = crypto.PKey()
            privateKey.generate_key(crypto.TYPE_RSA, 1024)
            password = ''
            while not password:
                try:
                    password = ask_password()
                    break
                except PasswordsDoNotMatch:
                    # Passwords did not match
                    pass

            encryption_args = password and ["DES-EDE3-CBC", password] or []
            privateKeyData = crypto.dump_privatekey(crypto.FILETYPE_PEM,
                                                    privateKey,
                                                    *encryption_args)
            open(config.private_key, 'w').write(privateKeyData)

            print "Generating configuration server SSL certificate"
            cert = crypto.X509()
            subject = cert.get_subject()
            subject.CN = 'SSHg Configuration Server'
            #cert.set_subject(subject)
            cert.set_pubkey(privateKey)
            cert.set_serial_number(0)
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(60 * 60 * 24 * 365 * 5) # Five Years
            cert.set_issuer(subject)
            cert.sign(privateKey, "md5")
            certData = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
            open(config.certificate, 'w').write(certData)
            print "Done. This certificate is valid for 5 years."
            print "You can provide your own private key/certificate,"
            print "just point to the correct paths on the configuration file."


        print "Creating Database"
        application.database_engine = create_engine()
        metadata.create_all(application.database_engine)
        print "Setup initial username"
        username = raw_input("Username [%s]: " % getpass.getuser())
        if not username:
            username = getpass.getuser()
        password = None
        while not password:
            try:
                password = ask_password('Define a password for "%s": ' %
                                        username)
                if not password:
                    print "Password cannot not be empty"
            except PasswordsDoNotMatch:
                pass

        Session = session()
        user = User(username, password, is_admin=True)
        pubkey_path = raw_input("Path to your public key [~/.ssh/id_rsa.pub]: ")
        if not pubkey_path:
            pubkey_path = expanduser('~/.ssh/id_rsa.pub')
        if not isfile(expanduser(pubkey_path)):
            print "File %r does not exist" % expanduser(pubkey_path)
        key = PublicKey(open(expanduser(pubkey_path)).read())
        user.keys.append(key)
        Session.add(user)
        Session.commit()
        print "Done"
        sys.exit()



class ServiceOptions(BaseOptions):
    longdesc = "Mercurial repositories SSH server"

    def getService(self):
        application.database_engine = create_engine()

        realm = MercurialRepositoriesRealm()
        portal = MercurialRepositoriesPortal(realm)
        portal.registerChecker(MercurialPublicKeysDB())
        factory = MercurialReposFactory(realm, portal)
        return internet.TCPServer(config.port, factory)

class SSHgOptions(BaseOptions):
    longdesc = "Mercurial repositories SSH server"

    optParameters = [
        ["config-dir", "c", None, "Configuration directory"],
    ]

    subCommands = [
        ["setup", None, SetupOptions, SetupOptions.longdesc],
        ["server", None, ServiceOptions, ServiceOptions.longdesc],
    ]
    defaultSubCommand = "server"

    def opt_config_dir(self, configdir):
        configdir = self.opts['config-dir'] = abspath(expanduser(configdir))
        configfile = join(configdir, 'sshg.ini')
        parser = SafeConfigParser()

        if not isdir(configdir):
            print "Creating configuration directory: %r" % configdir
            makedirs(configdir, 0750)

        if not isfile(configfile):
            print "Creating configuration file with defaults: %r" % configfile
            parser.add_section('main')
            parser.set('main', 'port', '22')
            parser.set('main', 'config_port', '8443')
            parser.set('main', 'discover_port', '8444')
            parser.set('main', 'host_port', '8445')
            parser.set('main', 'private_key', '%(here)s/privatekey.pem')
            parser.set('main', 'certificate', '%(here)s/certificate.pem')

            parser.add_section('database')
            parser.set('database', 'echo', 'false')
            parser.set('database', 'engine', 'sqlite')
            parser.set('database', 'username', '')
            parser.set('database', 'password', '')
            parser.set('database', 'name', 'database.db')
            parser.set('database', 'path', '%(here)s')
            parser.write(open(configfile, 'w'))
            print "Please check configuration and run the setup command"
            sys.exit(0)

        parser.read([configfile])
        parser.set('DEFAULT', 'here', configdir)

        config.dir = configdir
        config.static_dir = abspath(parser.get('main', 'static_dir'))
        config.port = parser.getint('main', 'port')
        config.config_port = parser.getint('main', 'config_port')
        config.discover_port = parser.getint('main', 'discover_port')
        config.host_port = parser.getint('main', 'host_port')
        config.private_key = abspath(parser.get('main', 'private_key'))
        config.certificate = abspath(parser.get('main', 'certificate'))

        config.db = ModuleType('config.db')
        config.db.echo = parser.getboolean('database', 'echo')
        config.db.engine = parser.get('database', 'engine')
        if config.db.engine not in ('sqlite', 'mysql', 'postgres', 'oracle',
                                    'mssql', 'firebird'):
            print 'Database engine "%s" not supported' % config.db.engine
            sys.exit(1)
        config.db.path = '/' + abspath(parser.get('database', 'path'))
        config.db.username = parser.get('database', 'username')
        config.db.password = parser.get('database', 'password')
        config.db.name = parser.get('database', 'name')


    def postOptions(self):
        if not self.opts.get('config-dir'):
            print "You need to pass a configuration directory. Exiting..."
            sys.exit(1)
        if not isfile(config.private_key) and self.subCommand != 'setup':
            print "The private key file(%r) does not exist" % config.private_key
            print "Did you run the setup command?"
            sys.exit(1)


class SSHgService(object):
    implements(IServiceMaker, IPlugin)
    tapname = 'sshg'
    description = __summary__
    options = SSHgOptions

    def makeService(self, options):
        app = Application("Mercurial SSH Server") #, uid, gid)
        services = IServiceCollection(app)
        if options.subCommand == 'server':
            # Run config server too?
#            config_factory = ConfigurationFactory()
#            config_service = internet.SSLServer(config.config_port,
#                                                config_factory,
#                                                config_factory)
#            config_service.setServiceParent(services)

            webconfig = SSHgWebConfigRoot()
            root = appserver.NevowSite(SSHgWebConfigRoot())
            webconfig_service = internet.SSLServer(config.config_port,
                                                   root, webconfig)
            webconfig_service.setServiceParent(services)

        service = options.subOptions.getService()
        service.setServiceParent(services)
        return services

