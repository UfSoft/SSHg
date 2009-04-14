# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.realms
    ~~~~~~~~~~~

    This module is responsible the needed authentication Realms.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.conch.manhole_ssh import TerminalRealm
from twisted.conch.interfaces import IConchUser
from twisted.conch.ssh.session import ISession
from twisted.python import components

from sshg.avatars import MercurialUser, MercurialAdmin
from sshg.sessions import (MercurialSession, MercurialAdminSession,
                           TerminalSessionTransport)
from sshg.database import User, session
from sshg import logger

log = logger.getLogger(__name__)

class MercurialRepositoriesRealm(TerminalRealm):
    transportFactory = TerminalSessionTransport

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IConchUser in interfaces:
            Session = session()
            user = Session.query(User).get(avatarId)
            if user.is_admin:
                log.debug("User %s is an admin", avatarId)
                self.userFactory = MercurialAdmin
                self.sessionFactory = MercurialAdminSession
            else:
                log.debug("User %s is a regular user", avatarId)
                self.userFactory = MercurialUser
                self.sessionFactory = MercurialSession
            Session.close()
            avatar = self._getAvatar(avatarId)
            return IConchUser, avatar, avatar.logout
        raise Exception, "No supported interfaces found."

    def _getAvatar(self, avatarId):
        comp = components.Componentized()
        user = self.userFactory(comp, avatarId)
        sess = self.sessionFactory(comp, user)

        sess.transportFactory = self.transportFactory
        sess.chainedProtocolFactory = self.chainedProtocolFactory

        comp.setComponent(IConchUser, user)
        comp.setComponent(ISession, sess)

        return user

