# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.database
    ~~~~~~~~~~~~~

    This module is a layer on top of SQLAlchemy to provide asynchronous
    access to the database and has the used tables/models used in SSHg

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import os
import sys
from os import path
from datetime import datetime
from types import ModuleType

import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import make_url, URL

from sshg import logger
from sshg.utils.crypto import gen_pwhash, check_pwhash

from twisted.conch.ssh.keys import Key
from twisted.python import log as twlog

log = logger.getLogger(__name__)

def get_engine():
    """Return the active database engine (the database engine of the active
    application).  If no application is enabled this has an undefined behavior.
    If you are not sure if the application is bound to the active thread, use
    :func:`~zine.application.get_application` and check it for `None`.
    The database engine is stored on the application object as `database_engine`.
    """
    from sshg.service import application
    return application.database_engine

def create_engine():
    from sshg.service import config
    if config.db.engine == 'sqlite':
        info = URL('sqlite', database=path.join(config.db.path, config.db.name))
    else:
        if config.db.username and config.db.password:
            uri = '%(engine)s://%(username)s:%(password)s@%(host)s/%(name)s'
        if config.db.username and not config.db.password:
            uri = '%(engine)s://%(username)s@%(host)s/%(name)s'
        else:
            uri = '%(engine)s://%(host)s/%(name)s'
        info = make_url(uri % config.db.__dict__)
    if info.drivername == 'mysql':
        info.query.setdefault('charset', 'utf8')
    options = {'convert_unicode': True, 'echo': config.db.echo}
    # alternative pool sizes / recycle settings and more.  These are
    # interpreter wide and not from the config for the following reasons:
    #
    # - system administrators can set it independently from the webserver
    #   configuration via SetEnv and friends.
    # - this setting is deployment dependent should not affect a development
    #   server for the same instance or a development shell
    for key in 'pool_size', 'pool_recycle', 'pool_timeout':
        value = os.environ.get('SSHG_DATABASE_' + key.upper())
        if value is not None:
            options[key] = int(value)
    return sqlalchemy.create_engine(info, **options)

def session():
    return orm.create_session(get_engine(), autoflush=True, autocommit=False)

def require_session(f):
    def wrapper(*args, **kwargs):
        current_session = session()
        try:
            return f(session=current_session, *args, **kwargs)
        except:
            twlog.err()
            current_session.rollback()
            raise   # We need to keep raising the exceptions, for now, all of them
        finally:
            current_session.close()
    return wrapper

#: create a new module for all the database related functions and objects
sys.modules['sshg.database.db'] = db = ModuleType('db')
key = value = mod = None
for mod in sqlalchemy, orm:
    for key, value in mod.__dict__.iteritems():
        if key in mod.__all__:
            setattr(db, key, value)
del key, mod, value


DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata


class SchemaVersion(DeclarativeBase):
    """SQLAlchemy-Migrate schema version control table."""

    __tablename__   = 'migrate_version'
    repository_id   = db.Column(db.String(255), primary_key=True)
    repository_path = db.Column(db.Text)
    version         = db.Column(db.Integer)

    def __init__(self, repository_id, repository_path, version):
        self.repository_id = repository_id
        self.repository_path = repository_path
        self.version = version


repousers_association = db.Table('repositories_users_association', metadata,
    db.Column('user_id', None, db.ForeignKey("repousers.username")),
    db.Column('repo_id', None, db.ForeignKey("repositories.name")),
)

repomanagers_association = db.Table(
    'repositories_managers_association', metadata,
    db.Column('user_id', None, db.ForeignKey("repousers.username")),
    db.Column('repo_id', None, db.ForeignKey("repositories.name")),
)


class Repository(DeclarativeBase):
    """Managed Repositories Table"""

    __tablename__ = 'repositories'

    name        = db.Column(db.String, primary_key=True)
    path        = db.Column(db.String, unique=True)
    size        = db.Column(db.Integer, default=0)
    quota       = db.Column(db.Integer, default=0)
    added_on    = db.Column(db.DateTime, default=datetime.utcnow())

    # Relationships
#    keys    = db.relation("PublicKey", secondary=repokeys_association,
#                          backref="repositories")
    users   = db.relation("User", secondary=repousers_association,
                          backref=orm.backref("repos", lazy='dynamic'))
    managers = db.relation("User", secondary=repomanagers_association,
                           backref=orm.backref("manages", lazy='dynamic'))

    def __init__(self, name, repo_path, size=0, quota=0):
        self.name = name
        self.path = repo_path
        self.size = size
        self.quota = quota

    def get_size(self, check=False):
        # For now, just return the database size. At a later stage, calculate it
        return self.size

    def __repr__(self):
        return \
        '<Repository Path: "%(path)s"  Size: %(size)s  Quota: %(quota)s>' % \
        self.__dict__


class PublicKey(DeclarativeBase):
    """Users Public Keys"""

    __tablename__ = 'pubkeys'

    key         = db.Column(db.String, primary_key=True)
    added_on    = db.Column(db.DateTime, default=datetime.utcnow())
    used_on     = db.Column(db.DateTime, default=datetime.utcnow())
    user_id     = db.Column(db.ForeignKey('repousers.username'))

#    # Many to Many Relation set elsewere
#    repositories = None

    def __init__(self, key_contents):
        self.key = Key.fromString(key_contents).toString("OPENSSH")

    def update_stamp(self):
        self.used_on = datetime.utcnow()

    def __repr__(self):
        return '<PublicKey "%s..." from "%s">' % (self.key.split()[1][5:],
                                                  self.owner.username)


class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'repousers'

    username        = db.Column(db.String, primary_key=True)
    password        = db.Column(db.String)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow())
    last_login      = db.Column(db.DateTime, default=datetime.utcnow())
    locked_out      = db.Column(db.Boolean, default=False)
    is_admin        = db.Column(db.Boolean, default=False)

    # Relationships
    keys            = db.relation("PublicKey", backref="owner",
                                  cascade="all, delete, delete-orphan")
    last_used_key   = db.relation("PublicKey", uselist=False)


    def __init__(self, username, password, is_admin=False):
        self.username = username
        self.password = gen_pwhash(password)
        self.is_admin = is_admin

    def authenticate(self, password):
        valid = check_pwhash(self.password, password)
        if valid:
            self.last_login = datetime.utcnow()
        return valid

    def change_password(self, password):
        self.password = gen_pwhash(password)

    def __repr__(self):
        return \
        '<User "%(username)s"  Admin: %(is_admin)s  Locked: %(locked_out)s>' % \
        self.__dict__

