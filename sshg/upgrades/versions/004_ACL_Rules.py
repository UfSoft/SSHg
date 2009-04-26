migrate_engine = object     # Make PyDev Happy
from sshg.upgrades.versions import *

DeclarativeBase = declarative_base()
DeclarativeBase.__table__ = None    # Make PyDev Happy
metadata = DeclarativeBase.metadata

class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'repousers'

    username        = db.Column(db.String, primary_key=True)
    password        = db.Column(db.String)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)
    locked_out      = db.Column(db.Boolean, default=False)
    is_admin        = db.Column(db.Boolean, default=False)

    # Relationships
    rules           = db.relation("AclRule", backref="user", lazy='dynamic',
                                  cascade="all, delete, delete-orphan")

class Repository(DeclarativeBase):
    """Managed Repositories Table"""

    __tablename__ = 'repositories'

    name            = db.Column(db.String, primary_key=True)
    path            = db.Column(db.String, unique=True)
    size            = db.Column(db.Integer, default=0)
    quota           = db.Column(db.Integer, default=0)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    incoming_quota  = db.Column(db.Integer, default=0)
    outgoing_quota  = db.Column(db.Integer, default=0)

    # Relationships
    rules    = db.relation("AclRule", backref="repo", lazy='dynamic',
                           cascade="all, delete, delete-orphan")

class AclRule(DeclarativeBase):
    __tablename__ = 'acl_rules'

    id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.ForeignKey('repousers.username'))
    repo_id = db.Column(db.ForeignKey('repositories.name'))
    sources = db.Column(db.String)
    allow   = db.Column(db.String)
    deny    = db.Column(db.String)

def upgrade():
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    AclRule.__table__.create(migrate_engine)

def downgrade():
    # Operations to reverse the above upgrade go here.
    AclRule.__table__.drop(migrate_engine)
