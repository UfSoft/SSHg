# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.realms
    ~~~~~~~~~~~

    This module is responsible the needed authentication Realms.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.conch.interfaces import IConchUser
from twisted.cred.portal import IRealm
from zope.interface import implements

from sshg.avatars import MercurialUser

class MercurialRepositoriesRealm(object):
    implements(IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IConchUser in interfaces:
            avatar = MercurialUser(avatarId)
            avatar.factory = self.factory
            return IConchUser, avatar, avatar.logout
        raise Exception, "No supported interfaces found."
