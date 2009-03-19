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
from twisted.python import log


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
            log.err()
            current_session.rollback()
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

repousers_association = db.Table('repositories_users_association', metadata,
    db.Column('user_id', None, db.ForeignKey("repousers.username")),
    db.Column('repo_id', None, db.ForeignKey("repositories.name"))
)

repokeys_association = db.Table('repositories_keys_association', metadata,
    db.Column('key_id', None, db.ForeignKey("pubkeys.key")),
    db.Column('repo_id', None, db.ForeignKey("repositories.name"))
)


class Repository(DeclarativeBase):
    """Managed Repositories Table"""

    __tablename__ = 'repositories'

    name    = db.Column(db.String, primary_key=True)
    path    = db.Column(db.String, unique=True)
    added   = db.Column(db.DateTime, default=datetime.utcnow())

    keys    = db.relation("PublicKey", secondary=repokeys_association,
                          backref="repositories")


class PublicKey(DeclarativeBase):
    """Users Public Keys"""

    __tablename__ = 'pubkeys'

    key     = db.Column(db.String, primary_key=True)
    added   = db.Column(db.DateTime, default=datetime.utcnow())
    used_on = db.Column(db.DateTime, default=datetime.utcnow())
    user_id = db.Column(db.ForeignKey('repousers.username'))

    # Many to Many Relation set elsewere
    repositories = None

    def __init__(self, key_contents):
        self.key = key_contents

    def update_stamp(self):
        self.used_on = datetime.utcnow()


class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'repousers'

    username        = db.Column(db.String, primary_key=True)
    added           = db.Column(db.DateTime, default=datetime.utcnow())
    last_login      = db.Column(db.DateTime, default=datetime.utcnow())

    # Relationships
    repositories    = db.relation("Repository", secondary=repousers_association,
                                  backref="users")
    keys            = db.relation("PublicKey", backref="owner",
                                  cascade="all, delete, delete-orphan")
    last_used_key   = db.relation("PublicKey", uselist=False)

    #query = session().query_property(Query)

    def __init__(self, username):
        self.username = username


class Session(DeclarativeBase):
    """Persistent Session Database"""
    __tablename__ = 'persistent_sessions'
    uid     = db.Column(db.String, primary_key=True)
    data    = db.Column(db.PickleType)

    #query = session().query_property(Query)

