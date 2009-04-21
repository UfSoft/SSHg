from sshg.upgrades.versions import *

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata

class Session(DeclarativeBase):
    """Persistent Session Database"""
    __tablename__ = 'persistent_sessions'

    uid     = db.Column(db.String, primary_key=True)
    data    = db.Column(db.PickleType)

def upgrade():
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    Session.__table__.drop(migrate_engine)

def downgrade():
    # Operations to reverse the above upgrade go here.
    Session.__table__.create(migrate_engine)

