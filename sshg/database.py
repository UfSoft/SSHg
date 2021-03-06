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
from uuid import uuid4

import sqlalchemy
from sqlalchemy import and_, or_
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import make_url, URL

from sshg import logger, exceptions, config
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
db.and_ = and_
db.or_ = or_
#del and_, or_


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

    name            = db.Column(db.String, primary_key=True)
    path            = db.Column(db.String, unique=True)
    size            = db.Column(db.Integer, default=0)
    quota           = db.Column(db.Integer, default=0)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_       = db.Column(db.ForeignKey('repousers.username'))
    incoming_quota  = db.Column(db.Integer, default=0)
    outgoing_quota  = db.Column(db.Integer, default=0)

    # Relationships
    users    = db.relation("User", secondary=repousers_association,
                           backref=orm.backref("repos", lazy='dynamic'))
    managers = db.relation("User", secondary=repomanagers_association,
                           backref=orm.backref("_manages", lazy='dynamic'))
    traffic  = db.relation("RepositoryTraffic",
                           backref=orm.backref("repo", lazy='dynamic'),
                           cascade="all, delete, delete-orphan")
    rules    = db.relation("AclRule", backref="repo", lazy='dynamic',
                           cascade="all, delete, delete-orphan")
    added_by = db.relation("User", backref="added_repos", uselist=False,
                           lazy=False)

    def __init__(self, name, repo_path, quota=0, incoming_quota=0,
                 outgoing_quota=0):
        self.name = name
        if not path.isdir(repo_path):
            raise exceptions.InvalidRepositoryPath
        elif not path.isdir(path.join(repo_path, '.hg')):
            raise exceptions.InvalidRepository
        else:
            self.path = repo_path.rstrip('/')
        self.quota = quota
        self.incoming_quota = incoming_quota
        self.outgoing_quota = outgoing_quota
        self.size = self.calculate_size()

    def calculate_size(self):
        dir_size = 0
        for (dirname, _, files) in os.walk(self.path):
            for filename in files:
                filepath = path.join(dirname, filename)
                dir_size += path.getsize(filepath)
        self.size = dir_size
        return self.size

    @property
    def over_quota(self):
        if self.quota == 0:
            return False
        return self.size > self.quota

    def __repr__(self):
        return ('<Repository Name: "%(name)s"  Path: "%(path)s"  '
                'Size: %(size)s  Quota: %(quota)s>' % self.__dict__)


class RepositoryTraffic(DeclarativeBase):
    """Repository Traffic"""

    __tablename__ = 'repository_traffic'
    stamp    = db.Column(db.DateTime, default=datetime.utcnow, primary_key=True)
    incoming = db.Column(db.Integer, default=0)
    outgoing = db.Column(db.Integer, default=0)
    repo_id  = db.Column(db.ForeignKey('repositories.name'))

    def __init__(self, incoming=0, outgoing=0):
        self.incoming = incoming
        self.outgoing = outgoing


class PublicKey(DeclarativeBase):
    """Users Public Keys"""

    __tablename__ = 'pubkeys'

    key         = db.Column(db.String, primary_key=True)
    added_on    = db.Column(db.DateTime, default=datetime.utcnow)
    used_on     = db.Column(db.DateTime, default=datetime.utcnow)
    user_id     = db.Column(db.ForeignKey('repousers.username'))

    # Relationships defined on other classes
    owner = None

    def __init__(self, key_contents):
        self.key = Key.fromString(key_contents).toString("OPENSSH")
        if not self.key:
            raise Exception("Invalid Key")

    def update_stamp(self):
        self.used_on = datetime.utcnow()

    def __repr__(self):
        return '<PublicKey "%s..." from "%s">' % (self.key.split()[1][5:],
                                                  self.owner.username)


class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'repousers'

    username         = db.Column(db.String, primary_key=True)
    uuid             = db.Column(db.String(32), default=lambda: uuid4().hex)
    email            = db.Column(db.String)
    password         = db.Column(db.String)
    added_on         = db.Column(db.DateTime, default=datetime.utcnow)
    creator          = db.Column(db.ForeignKey('repousers.username'))
    last_login       = db.Column(db.DateTime, default=datetime.utcnow)
    locked_out       = db.Column(db.Boolean, default=False)
    is_admin         = db.Column(db.Boolean, default=False)

    # Relationships
    created_accounts = db.relation("User", backref=db.backref(
                                       "created_by",
                                       remote_side="User.username"))
    keys             = db.relation("PublicKey", backref="owner",
                                   cascade="all, delete, delete-orphan")
    last_used_key    = db.relation("PublicKey", uselist=False)
    rules            = db.relation("AclRule", backref="user", lazy='dynamic',
                                   cascade="all, delete, delete-orphan")
    session          = db.relation("Session", lazy=True, uselist=False,
                                   backref=db.backref('user', uselist=False),
                                   cascade="all, delete, delete-orphan")
    changes          = db.relation("Change", backref='owner', lazy='dynamic',
                                   cascade="all, delete")

    # Relationships defined on other classes
    _manages = None


    def __init__(self, username, password, email, is_admin=False,
                 created_by=None):
        self.username = username
        self.password = gen_pwhash(password)
        self.email = email
        self.is_admin = is_admin
        self.created_by = created_by

    def authenticate(self, password):
        valid = check_pwhash(self.password, password)
        if valid:
            self.last_login = datetime.utcnow()
        return valid

    def change_password(self, password):
        self.password = gen_pwhash(password)

    def __repr__(self):
        return ('<User "%(username)s"  Admin: %(is_admin)s  '
                'Locked: %(locked_out)s>' % self.__dict__)

    @property
    def manages(self):
        if self.is_admin:
            return session().query(Repository)
        return self._manages.filter(User.username==self.username)

    @property
    def is_manager(self):
        if self.is_admin:
            return True
        return self.manages.count() > 0

    @property
    def is_app_admin(self):
        return self.username == config.app_manager

    def can_be_managed_by(self, user):
        if self.is_app_admin and not user.is_app_admin:
            # Non application admins cannot delete the application admin
            return False
        # A user cannot manage(delete) himself but can manage accounts
        # he created. If `user` is the application admin, he can manage anyone
        return user is not self and (user.is_admin or
                                     self in user.created_accounts)

class Change(DeclarativeBase):
    __tablename__ = 'user_changes'

    hash        = db.Column('id', db.String(32), primary_key=True)
    changes     = db.Column(db.PickleType)
    created     = db.Column(db.DateTime, default=datetime.utcnow)
    owner_uid   = db.Column(None, db.ForeignKey('repousers.username'))

    # ForeignKey Association
    owner = None # Defined on User.changes

    def __init__(self, change_data):
        self.hash = uuid4().hex
        if not isinstance(change_data, dict):
            raise Exception("Change data must be a dictionary.")
        self.changes = change_data

    def __url__(self, include_hash=True, **kwargs):
        from sshg.web.utils import url_for
        return url_for('account.confirm',
                       confirm_hash=include_hash and self.hash or None,
                       **kwargs)

    def __repr__(self):
        return '<UserChange Dated %s  DATA: %r>' % (self.created, self.changes)

class AclRule(DeclarativeBase):
    __tablename__ = 'acl_rules'

    id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order   = db.Column(db.Integer, default=0)
    sources = db.Column(db.String)
    allow   = db.Column(db.String)
    deny    = db.Column(db.String)
    user_id = db.Column(db.ForeignKey('repousers.username'))
    repo_id = db.Column(db.ForeignKey('repositories.name'))


class Session(DeclarativeBase):
    __tablename__ = 'session'

    user_uuid       = db.Column(db.ForeignKey('repousers.uuid'),
                                primary_key=True)
    last_visit      = db.Column(db.DateTime, default=datetime.utcnow)
    language        = db.Column(db.String(5), default='en_US')
    datetime_format = db.Column(db.String(25), default='%Y-%m-%d %H:%M:%S')

    def update_last_visit(self):
        self.last_visit = datetime.utcnow()
