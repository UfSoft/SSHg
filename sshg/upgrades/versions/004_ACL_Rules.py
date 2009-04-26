migrate_engine = object     # Make PyDev Happy
from sshg.upgrades.versions import *

DeclarativeBase = declarative_base()
DeclarativeBase.__table__ = None    # Make PyDev Happy
metadata = DeclarativeBase.metadata

class ACLRules(DeclarativeBase):
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
    ACLRules.__table__.create(migrate_engine)

def downgrade():
    # Operations to reverse the above upgrade go here.
    ACLRules.__table__.drop(migrate_engine)
