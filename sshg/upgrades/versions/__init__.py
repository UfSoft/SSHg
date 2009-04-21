import sys
from datetime import datetime
from types import ModuleType
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base
from migrate import *
from migrate import changeset, versioning

sys.modules['sshg.database.db'] = db = ModuleType('db')
key = value = mod = None
for mod in sqlalchemy, orm, versioning, changeset:
    for key, value in mod.__dict__.iteritems():
        try:
            if key in mod.__all__:
                setattr(db, key, value)
        except AttributeError:
            if key in dir(mod):
                setattr(db, key, value)
del key, mod, value
