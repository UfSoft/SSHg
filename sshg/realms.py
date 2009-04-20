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
from twisted.internet import defer
from twisted.python import components, log as twlog

from sshg.avatars import MercurialUser, MercurialAdmin
from sshg.sessions import MercurialSession, MercurialAdminSession
from sshg.database import User, session
from sshg import logger, database as db

log = logger.getLogger(__name__)

class MercurialRepositoriesRealm(TerminalRealm):

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IConchUser in interfaces:
            d = defer.maybeDeferred(db.session)
            d.addCallback(self._cbRequestAvatar, avatarId)
            d.addErrback(self._ebRequestAvatar)
            return d
        raise Exception("No supported interfaces found.")

    def _cbRequestAvatar(self, session, avatarId):
        user = session.query(db.User).get(avatarId)
        if not user:
            return defer.fail(Exception("User is not known"))
        elif user.locked_out:
            return defer.fail(Exception("User locked out"))
        elif user.is_admin or user.manages.first():
            log.debug("User %s is %s", avatarId,
                      user.is_admin and 'admin' or 'manager')
            self.userFactory = MercurialAdmin
            self.sessionFactory = MercurialAdminSession
        else:
            log.debug("User %s is a regular user", avatarId)
            self.userFactory = MercurialUser
            self.sessionFactory = MercurialSession
        session.close()
        avatar = self._getAvatar(avatarId)
        return defer.succeed((IConchUser, avatar, avatar.logout))

    def _ebRequestAvatar(self, failure):
        try:
            twlog.err()
        except:
            log.error(failure)
        return failure

    def _getAvatar(self, avatarId):
        comp = components.Componentized()
        user = self.userFactory(comp, avatarId)

        sess = self.sessionFactory(comp, user)
        sess.transportFactory = self.transportFactory
        sess.chainedProtocolFactory = self.chainedProtocolFactory

        comp.setComponent(IConchUser, user)
        comp.setComponent(ISession, sess)

        return user

