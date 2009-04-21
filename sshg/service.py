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
from os.path import abspath, basename, expanduser, isdir, isfile, join
from types import ModuleType

from twisted.application import internet
from twisted.application.service import (IServiceMaker, Application,
                                         IServiceCollection)
from twisted.plugin import IPlugin
from twisted.python import usage
from zope.interface import implements


from sshg import (__version__, __summary__, application, config, database as db,
                  upgrades)
from sshg.checkers import MercurialAuthenticationChekers
from sshg.factories import MercurialReposFactory
from sshg.portals import MercurialRepositoriesPortal
from sshg.realms import MercurialRepositoriesRealm


try:
    from migrate.versioning.api import upgrade
    from migrate.versioning.repository import Repository

    UPGRADES_REPO = Repository(upgrades.__path__[0])
except ImportError:
    print "You need the SQLAlchemy-migrate package installed."
    print "  http://code.google.com/p/sqlalchemy-migrate/"
    sys.exit(1)

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

            print "You can provide your own private key."
            print "Just point to the correct paths on the configuration file."


        print "Creating Database"
        application.database_engine = db.create_engine()
        db.metadata.create_all(application.database_engine)
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

        session = db.session()
        user = db.User(username, password, is_admin=True)
        pubkey_path = raw_input("Path to your public key [~/.ssh/id_rsa.pub]: ")
        if not pubkey_path:
            pubkey_path = expanduser('~/.ssh/id_rsa.pub')
        if not isfile(expanduser(pubkey_path)):
            print "File %r does not exist" % expanduser(pubkey_path)
        key = db.PublicKey(open(expanduser(pubkey_path)).read())
        user.keys.append(key)
        session.add(user)

        # Setup database schema version control
        session.add(db.SchemaVersion("SSHg Schema Version Control",
                                     UPGRADES_REPO.path, UPGRADES_REPO.latest)
        )

        session.commit()
        print "Done"
        sys.exit()

class MigrateScriptAccess(BaseOptions):
    longdesc = "SQLAlchemy Migrate Script Access"

    def parseOptions(self, options=None):
        from migrate.versioning.shell import main
        # Tweak sys.argv
        sys.argv = sys.argv[sys.argv.index('migrate'):]
        main(url=db.create_engine().url, repository=UPGRADES_REPO.path)
        sys.exit()

class UpgradeOptions(BaseOptions):
    longdesc = "Upgrade SSHg"

    subCommands = [
        ["migrate", None, MigrateScriptAccess, MigrateScriptAccess.longdesc]
    ]

    def getService(self):
        application.database_engine = db.create_engine()
        session = db.session()
        if not application.database_engine.has_table(
                                                db.SchemaVersion.__tablename__):
            # Too old db schema version, does not even have the control table
            db.SchemaVersion.__table__.create(bind=application.database_engine)

        if not session.query(db.SchemaVersion).first():
            # No previously entered record
            session.add(
                db.SchemaVersion("SSHg Schema Version Control",
                                 unicode(UPGRADES_REPO.path), 0)
            )
            session.commit()

        schema_version = session.query(db.SchemaVersion).first()

        if schema_version.version >= UPGRADES_REPO.latest:
            print "No upgrade needed."
            sys.exit()

        # Do the database upgrade
        if config.db.engine == 'sqlite':
            from shutil import copy
            print "Backup current database:"
            old_db_path = join(config.db.path, config.db.name)
            new_db_path = join(config.db.path, '.'.join(
                [config.db.name, str(UPGRADES_REPO.latest), 'bak'])
            )
            print " %s -> %s" % (old_db_path, new_db_path)
            copy(old_db_path, new_db_path)
        print "Upgrading..."
        upgrade(application.database_engine.url, UPGRADES_REPO)

        sys.exit()

class ServiceOptions(BaseOptions):
    longdesc = "Mercurial repositories SSH server"

    def getService(self):

        def upgrade_required():
            print "You need to upgrade your database!"
            print "Please run the upgrade command"
            sys.exit(1)
        application.database_engine = db.create_engine()

        session = db.session()
        if not application.database_engine.has_table(
                                                db.SchemaVersion.__tablename__):
            # Too old db schema version, does not even have the control table
            upgrade_required()
        elif not session.query(db.SchemaVersion).first():
            # Table exists!? Yet, no previously entered record!?
            upgrade_required()

        schema_version = session.query(db.SchemaVersion).first()
        if schema_version.version < UPGRADES_REPO.latest:
            upgrade_required()

        realm = MercurialRepositoriesRealm()
        portal = MercurialRepositoriesPortal(realm)
        portal.registerChecker(MercurialAuthenticationChekers())
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
        ["upgrade", None, UpgradeOptions, UpgradeOptions.longdesc],
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
            parser.set('main', 'private_key', '%(here)s/privatekey.pem')
            parser.set('main', 'motd_file', '%(here)s/motd.txt')

            motd_file = join(configdir, 'motd.txt')
            if not isfile(motd_file):
                open(motd_file, 'w').write(
                    "%(green)s  Welcome to the SSHg console terminal. "
                    "Type ? for help."
                )

            parser.add_section('database')
            parser.set('database', 'echo', 'false')
            parser.set('database', 'engine', 'sqlite')
            parser.set('database', 'username', '')
            parser.set('database', 'password', '')
            parser.set('database', 'name', 'database.db')
            parser.set('database', 'path', '%(here)s')
            parser.write(open(configfile, 'w'))
            print "Please check configuration and run the setup command again"
            sys.exit(0)

        parser.read([configfile])
        parser.set('DEFAULT', 'here', configdir)

        config.dir = configdir
        config.port = parser.getint('main', 'port')
        config.private_key = abspath(parser.get('main', 'private_key'))

        motd = abspath(parser.get('main', 'motd_file'))
        if isfile(motd):
            config.motd = open(motd).read()
        else:
            config.motd = "%(green)s  Welcome to the SSHg console terminal. "+ \
                          "Type ? for help."

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
        service = options.subOptions.getService()
        service.setServiceParent(services)
        return services

