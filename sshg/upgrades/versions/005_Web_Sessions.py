migrate_engine = object     # Make PyDev Happy
from os.path import join
from uuid import uuid4
from shutil import copy2
from OpenSSL import crypto
from sshg import config
from sshg.utils.crypto import gen_secret_key
from sshg.upgrades.versions import *

DeclarativeBase = declarative_base()
DeclarativeBase.__table__ = None    # Make PyDev Happy
metadata = DeclarativeBase.metadata

class User(DeclarativeBase):
    """Repositories users table"""
    __tablename__ = 'repousers'

    username        = db.Column(db.String, primary_key=True)
    uuid            = db.Column(db.String(32), default=lambda: uuid4().hex)
    email           = db.Column(db.String)
    password        = db.Column(db.String)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)
    locked_out      = db.Column(db.Boolean, default=False)
    is_admin        = db.Column(db.Boolean, default=False)
    confirmed       = db.Column(db.Boolean, default=False)

    # Relationships
    session         = db.relation("Session", lazy=True, uselist=False,
                                  backref=db.backref('user', uselist=False),
                                  cascade="all, delete, delete-orphan")
    changes         = db.relation("Change", backref='owner',
                                  cascade="all, delete, delete-orphan")

class Change(DeclarativeBase):
    __tablename__ = 'user_changes'

    hash        = db.Column('id', db.String(32), primary_key=True)
    name        = db.Column(db.String)
    value       = db.Column(db.String)
    created     = db.Column(db.DateTime, default=datetime.utcnow)
    owner_uid   = db.Column(None, db.ForeignKey('repousers.username'))

class Session(DeclarativeBase):
    __tablename__ = 'session'

    user_uuid       = db.Column(db.ForeignKey('repousers.uuid'),
                                primary_key=True)
    last_visit      = db.Column(db.DateTime, default=datetime.utcnow)
    language        = db.Column(db.String(5), default='en_US')
    datetime_format = db.Column(db.String(25), default='%Y-%m-%d %H:%M:%S')


def upgrade():
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    backup_cfg_file = config.file + '.bak'
    print
    print "Backup current configuration %r -> %r" % (config.file,
                                                     backup_cfg_file)
    copy2(config.file, backup_cfg_file)
    print "Upgrading configuration. Please review it!"
    parser = config.parser
    if not parser.has_section('web'):
        parser.add_section('web')
    parser.set('web', 'port', '8443')
    parser.set('web', 'certificate', '%(here)s/certificate.pem')
    parser.set('web', 'cookie_name', 'SSHg')
    parser.set('web', 'secret_key', gen_secret_key())
    parser.set('web', 'min_threads', '5')
    parser.set('web', 'max_threads', '25')
    parser.add_section('notification')
    parser.set('notification', 'enabled', 'true')
    parser.set('notification', 'smtp_server', '')
    parser.set('notification', 'smtp_port', '25')
    parser.set('notification', 'smtp_user', '')
    parser.set('notification', 'smtp_pass', '')
    parser.set('notification', 'smtp_from', '')
    parser.set('notification', 'from_name', 'SSHg')
    parser.set('notification', 'reply_to', '')
    parser.set('notification', 'use_tls', 'false')
    parser.remove_option('DEFAULT', 'here')
    parser.write(open(config.file, 'w'))
    print "Generating configuration server SSL certificate"
    cert = crypto.X509()
    subject = cert.get_subject()
    subject.CN = 'SSHg Configuration Server'
    from sshg.service import ask_password
    privateKey = crypto.load_privatekey(crypto.FILETYPE_PEM,
                                        open(config.private_key).read(),
                                        ask_password)
    cert.set_pubkey(privateKey)
    cert.set_serial_number(2)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(60 * 60 * 24 * 365 * 5) # Five Years
    cert.set_issuer(subject)
    cert.sign(privateKey, "md5")
    certData = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    open(join(config.dir, 'certificate.pem'), 'w').write(certData)
    print "Done. This certificate is valid for 5 years."
    print "You can provide your own private key/certificate,"
    print "just point to the correct paths on the configuration file."
    print

    print "Upgrading Database"
    metadata.bind = migrate_engine # bind the engine

    Change.__table__.create(migrate_engine)
    Session.__table__.create(migrate_engine)
    User.__table__.c.uuid.create(User.__table__)
    User.__table__.c.email.create(User.__table__)
    User.__table__.c.confirmed.create(User.__table__)

    session = db.create_session(migrate_engine, autoflush=True,
                                autocommit=False)
    for user in session.query(User).all():
        user.uuid = uuid4().hex
        user.confirmed = True
        user.session = Session()
    session.commit()

def downgrade():
    # Operations to reverse the above upgrade go here.
    parser = config.parser
    if parser.has_section('web'):
        parser.remove_section('web')
    if parser.has_section('notification'):
        parser.remove_section('notification')
    parser.remove_option('DEFAULT', 'here')
    parser.write(open(config.file, 'w'))

    metadata.bind = migrate_engine # bind the engine
    Change.__table__.drop(migrate_engine)
    Session.__table__.drop(migrate_engine)
    User.__table__.c.uuid.drop(User.__table__)
    User.__table__.c.email.drop(User.__table__)
    User.__table__.c.confirmed.drop(User.__table__)
