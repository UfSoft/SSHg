import sys
from datetime import datetime
from types import ModuleType
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from migrate import *

sys.modules['sshg.database.db'] = db = ModuleType('db')
key = value = mod = None
for mod in sqlalchemy, orm:
    for key, value in mod.__dict__.iteritems():
        if key in mod.__all__:
            setattr(db, key, value)
del key, mod, value
