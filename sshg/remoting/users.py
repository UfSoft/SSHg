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

class UsersResource(Resource):

    @require_session
    def get_all(self, session=None):
        users = []
        for user in session.query(User).all():
            log.debug(user)
            data = {}
            for key in ['username', 'password', 'added_on', 'last_login',
                        'is_admin', 'locked_out']:
                data[key] = getattr(user, key)
            users.append(data)
        return ArrayCollection(users)

