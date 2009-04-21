from sshg.upgrades.versions import *

DeclarativeBase = declarative_base()
DeclarativeBase.__table__ = None    # Make PyDev Happy
metadata = DeclarativeBase.metadata


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
    added_on        = db.Column(db.DateTime, default=datetime.utcnow())
    incoming_quota  = db.Column(db.Integer, default=0)
    outgoing_quota  = db.Column(db.Integer, default=0)

    # Relationships
#    keys    = db.relation("PublicKey", secondary=repokeys_association,
#                          backref="repositories")
#    users    = db.relation("User", secondary=repousers_association,
#                           backref=orm.backref("repos", lazy='dynamic'))
#    managers = db.relation("User", secondary=repomanagers_association,
#                           backref=orm.backref("manages", lazy='dynamic'))
    traffic  = db.relation("RepositoryTraffic",
                           backref=orm.backref("repo", lazy='dynamic'),
                           cascade="all, delete, delete-orphan")


class RepositoryTraffic(DeclarativeBase):
    """Repository Traffic"""

    __tablename__ = 'repository_traffic'
    stamp    = db.Column(db.DateTime, default=datetime.utcnow(),
                         primary_key=True)
    incoming = db.Column(db.Integer, default=0)
    outgoing = db.Column(db.Integer, default=0)
    repo_id  = db.Column(db.ForeignKey('repositories.name'))


def upgrade():
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    metadata.bind = migrate_engine # We need to bind the engine
    Repository.__table__.c.incoming_quota.create(Repository.__table__)
    Repository.__table__.c.outgoing_quota.create(Repository.__table__)
    RepositoryTraffic.__table__.create(migrate_engine)
    session = db.create_session(migrate_engine, autoflush=True,
                                autocommit=False)
    # Set the column default values
    for entry in session.query(Repository).all():
        entry.incoming_quota = entry.outgoing_quota = 0
    session.commit()


def downgrade():
    # Operations to reverse the above upgrade go here.
    metadata.bind = migrate_engine # We need to bind the engine
    Repository.__table__.c.incoming_quota.drop(Repository.__table__)
    Repository.__table__.c.outgoing_quota.drop(Repository.__table__)
    RepositoryTraffic.__table__.drop(migrate_engine)
