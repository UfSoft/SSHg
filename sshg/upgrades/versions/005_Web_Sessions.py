migrate_engine = object     # Make PyDev Happy
from os.path import join
from uuid import uuid4
from shutil import copy2
from OpenSSL import crypto
from sshg import config
from sshg.utils.crypto import gen_secret_key
from sshg.upgrades.versions import *

DeclarativeBase1 = declarative_base()
DeclarativeBase1.__table__ = None    # Make PyDev Happy
metadata1 = DeclarativeBase1.metadata

DeclarativeBase2 = declarative_base()
DeclarativeBase2.__table__ = None    # Make PyDev Happy
metadata2 = DeclarativeBase2.metadata

class NewUsers(DeclarativeBase2):
    """Repositories users table"""
    __tablename__ = 'repousers'

    username        = db.Column(db.String, primary_key=True)
    uuid            = db.Column(db.String(32), default=lambda: uuid4().hex)
    email           = db.Column(db.String)
    password        = db.Column(db.String)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    creator         = db.Column(db.String, db.ForeignKey('repousers.username'))
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)
    locked_out      = db.Column(db.Boolean, default=False)
    is_admin        = db.Column(db.Boolean, default=False)

    # Relationships
    created_accounts = db.relation("NewUsers",
                                   backref=db.backref(
                                        "created_by",
                                        remote_side="NewUsers.username"))

    session         = db.relation("Session", lazy=True, uselist=False,
                                  backref=db.backref('user', uselist=False),
                                  cascade="all, delete, delete-orphan")
    changes         = db.relation("Change", backref='owner',
                                  cascade="all, delete, delete-orphan")

    def __init__(self, username, password, email, is_admin=False,
                 created_by=None):
        self.username = username
        self.password = password
        self.email = email
        self.is_admin = is_admin
        self.created_by = created_by

    def __repr__(self):
        return ('<User "%(username)s"  Admin: %(is_admin)s  '
                'Locked: %(locked_out)s>' % self.__dict__)

class OldUser(DeclarativeBase1):
    """Repositories users table"""
    __tablename__ = 'repousers'

    username        = db.Column(db.String, primary_key=True)
    password        = db.Column(db.String)
    added_on        = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, default=datetime.utcnow)
    locked_out      = db.Column(db.Boolean, default=False)
    is_admin        = db.Column(db.Boolean, default=False)

    def __init__(self, username, password, is_admin=False):
        self.username = username
        self.password = password
        self.is_admin = is_admin


class Change(DeclarativeBase2):
    __tablename__ = 'user_changes'

    hash        = db.Column('id', db.String(32), primary_key=True)
    changes     = db.Column(db.PickleType)
    created     = db.Column(db.DateTime, default=datetime.utcnow)
    owner_uid   = db.Column(None, db.ForeignKey('repousers.username'))

class Session(DeclarativeBase2):
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
    if not parser.has_section('notification'):
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
    metadata1.bind = migrate_engine # bind the engine
    metadata2.bind = migrate_engine # bind the engine

    Change.__table__.create(migrate_engine)
    Session.__table__.create(migrate_engine)

    OldUser.__table__.rename('repousers_old')
    NewUsers.__table__.create(migrate_engine)

    session = db.create_session(migrate_engine, autoflush=True,
                                autocommit=False)

    for user in session.query(OldUser).all():
        new_user = NewUsers(
            user.username,
            user.password,
            getattr(user, 'email', None),
            user.is_admin)
        new_user.session = Session()
        new_user.added_on = user.added_on
        new_user.last_login = user.last_login
        session.add(new_user)
    session.commit()

    admin = session.query(NewUsers).filter_by(is_admin=True). \
            order_by(NewUsers.__table__.c.added_on.asc()).first()
    for user in session.query(NewUsers).all():
        if user.uuid != admin.uuid:
            user.creator = admin.username
    session.commit()

    OldUser.__table__.drop(migrate_engine)

    parser.set('main', 'app_manager', admin.username)
    parser.write(open(config.file, 'w'))

def downgrade():
    # Operations to reverse the above upgrade go here.
    parser = config.parser
    if parser.has_section('web'):
        parser.remove_section('web')
    if parser.has_section('notification'):
        parser.remove_section('notification')
    parser.remove_option('DEFAULT', 'here')
    parser.write(open(config.file, 'w'))

    metadata1.bind = migrate_engine # bind the engine
    metadata2.bind = migrate_engine # bind the engine
    Change.__table__.drop(migrate_engine)
    Session.__table__.drop(migrate_engine)

    session = db.create_session(migrate_engine, autoflush=True,
                                autocommit=False)

    old_users = session.query(NewUsers).all()


    NewUsers.__table__.rename('repousers_old')
    OldUser.__table__.create(migrate_engine)

    for user in old_users:
        new_user = OldUser(
            user.username,
            user.password,
            user.is_admin)
        new_user.added_on = user.added_on
        session.add(new_user)
    session.commit()

    NewUsers.__table__.drop(migrate_engine)
