#__import__('pkg_resources').declare_namespace(__name__)

from sshg import database
from utils import local_manager
from sqlalchemy.orm import scoped_session

session = scoped_session(lambda: database.session(), local_manager.get_ident)
