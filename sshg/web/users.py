# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.web.users
    ~~~~~~~~~~~~~~

    This module holds the users web management.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from sshg.database import require_session, User
from sshg.web.base import SSHgWebConfigBase

class SSHgUsers(SSHgWebConfigBase):

    contentTemplateFile = 'users_list.html'

    hrefHdlr = 'users'
    hrefName = 'Users'
    title = 'Users List'

    @require_session
    def data_users(self, context, data, session=None):
        print '\ncalled data_users'
        return session.query(User).all()

    def render_user(self, context, data):
        context.tag.fillSlots('username', data.username)
        context.tag.fillSlots('added_on', str(data.added_on))
        context.tag.fillSlots('last_login', str(data.last_login))
        context.tag.fillSlots('locked_out', data.locked_out)
        context.tag.fillSlots('is_admin', data.is_admin)
        return context.tag
