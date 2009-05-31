migrate_engine = object     # Make PyDev Happy
from OpenSSL import crypto
from sshg.upgrades.versions import *

DeclarativeBase1 = declarative_base()
DeclarativeBase1.__table__ = None    # Make PyDev Happy
metadata1 = DeclarativeBase1.metadata

DeclarativeBase2 = declarative_base()
DeclarativeBase2.__table__ = None    # Make PyDev Happy
metadata2 = DeclarativeBase2.metadata

class RepositoryOld(DeclarativeBase1):
    """Managed Repositories Table"""

    __tablename__ = 'repositories'

    name            = db.Column(db.String, primary_key=True)
    path            = db.Column(db.String, unique=True)
    size            = db.Column(db.Integer, default=0)
    quota           = db.Column(db.Integer, default=0)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    incoming_quota  = db.Column(db.Integer, default=0)
    outgoing_quota  = db.Column(db.Integer, default=0)

    def __init__(self, name, repo_path, quota, size, incoming_quota,
                 outgoing_quota):
        self.name = name
        self.path = repo_path
        self.quota = quota
        self.size = size
        self.incoming_quota = incoming_quota
        self.outgoing_quota = outgoing_quota

class RepositoryNew(DeclarativeBase2):
    """Managed Repositories Table"""

    __tablename__ = 'repositories'

    name            = db.Column(db.String, primary_key=True)
    path            = db.Column(db.String, unique=True)
    size            = db.Column(db.Integer, default=0)
    quota           = db.Column(db.Integer, default=0)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_       = db.Column(db.String, db.ForeignKey('repousers.username'))
    incoming_quota  = db.Column(db.Integer, default=0)
    outgoing_quota  = db.Column(db.Integer, default=0)

    def __init__(self, name, repo_path, quota, size, incoming_quota,
                 outgoing_quota):
        self.name = name
        self.path = repo_path
        self.quota = quota
        self.size = size
        self.incoming_quota = incoming_quota
        self.outgoing_quota = outgoing_quota

class NewUsers(DeclarativeBase2):
    """Repositories users table"""
    __tablename__ = 'repousers'

    username        = db.Column(db.String, primary_key=True)
    uuid            = db.Column(db.String(32))
    email           = db.Column(db.String)
    password        = db.Column(db.String)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    creator         = db.Column(db.String, db.ForeignKey('repousers.username'))
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)
    locked_out      = db.Column(db.Boolean, default=False)
    is_admin        = db.Column(db.Boolean, default=False)


def upgrade():
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.

    print
    print "Upgrading Database"
    metadata1.bind = migrate_engine # bind the engine
    metadata2.bind = migrate_engine # bind the engine

    session = db.create_session(migrate_engine, autoflush=True,
                                autocommit=False)

    admin = session.query(NewUsers).filter_by(is_admin=True). \
            order_by(NewUsers.__table__.c.added_on.asc()).first()

    oldrepos = session.query(RepositoryOld).all()

    RepositoryOld.__table__.rename('repositories_old')
    RepositoryNew.__table__.create(migrate_engine)

    for repo in oldrepos:
        newrepo = RepositoryNew(repo.name,
                                repo.path,
                                repo.quota,
                                repo.size,
                                repo.incoming_quota,
                                repo.outgoing_quota)
        newrepo.added_by_ = admin.username
        session.add(newrepo)
    session.commit()
    RepositoryOld.__table__.drop(migrate_engine)


def downgrade():
    # Operations to reverse the above upgrade go here.

    metadata1.bind = migrate_engine # bind the engine
    metadata2.bind = migrate_engine # bind the engine

    session = db.create_session(migrate_engine, autoflush=True,
                                autocommit=False)

    oldrepos = session.query(RepositoryNew).all()

    RepositoryNew.__table__.rename('repositories_old')
    RepositoryOld.__table__.create(migrate_engine)

    for repo in oldrepos:
        newrepo = RepositoryOld(repo.name,
                                repo.path,
                                repo.quota,
                                repo.size,
                                repo.incoming_quota,
                                repo.outgoing_quota)
        session.add(newrepo)
    session.commit()
    RepositoryNew.__table__.drop(migrate_engine)
