from sshg.upgrades.versions import *

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata


repousers_association = db.Table('repositories_users_association', metadata,
    db.Column('user_id', None, db.ForeignKey("repousers.username")),
    db.Column('repo_id', None, db.ForeignKey("repositories.name")),
)

repomanagers_association = db.Table('repositories_managers_association', metadata,
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

class PublicKey(DeclarativeBase):
    """Users Public Keys"""

    __tablename__ = 'pubkeys'

    key         = db.Column(db.String, primary_key=True)
    added_on    = db.Column(db.DateTime, default=datetime.utcnow())
    used_on     = db.Column(db.DateTime, default=datetime.utcnow())
    user_id     = db.Column(db.ForeignKey('repousers.username'))

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
#    repositories    = db.relation("Repository", secondary=repousers_association,
#                                  backref="users")
    keys            = db.relation("PublicKey", backref="owner",
                                  cascade="all, delete, delete-orphan")
    last_used_key   = db.relation("PublicKey", uselist=False)


class Session(DeclarativeBase):
    """Persistent Session Database"""
    __tablename__ = 'persistent_sessions'

    uid     = db.Column(db.String, primary_key=True)
    data    = db.Column(db.PickleType)

def upgrade():
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    metadata.create_all(migrate_engine)

def downgrade():
    # Operations to reverse the above upgrade go here.
    metadata.drop_all(migrate_engine)
