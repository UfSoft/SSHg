# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.remoting.users
    ~~~~~~~~~~~~~~~~~~~

    This module holds the users remote management.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from sshg.remoting import *
from sshg.database import User

log = logger.getLogger(__name__)
import pyamf

class UsersResource(Resource):

    @require_session
    def get_all(self, session=None):
        klass = pyamf.load_class("org.ufsoft.sshg.models.RepositoryUser").klass
        users = ArrayCollection()
        for user in session.query(klass).all():
            log.debug(user)
            users.addItem(user)
        return session.query(klass).all()

