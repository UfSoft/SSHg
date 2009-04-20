# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.factories
    ~~~~~~~~~~~~~~

    This module is responsible the service authentication chekers.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.conch.error import ValidPublicKey
from twisted.conch.ssh import keys
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.credentials import IUsernamePassword, ISSHPrivateKey
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer
from twisted.python import failure, log as twlog

from zope.interface import implements

from sshg import database as db, logger

log = logger.getLogger(__name__)


class MercurialAuthenticationChekers(object):
    credentialInterfaces = ISSHPrivateKey, IUsernamePassword
    implements(ICredentialsChecker)

    def requestAvatarId(self, credentials):
        d = defer.maybeDeferred(db.session)
        if hasattr(credentials, 'password'):
            d.addCallback(self.authenticate, credentials)
        else:
            d.addCallback(self.checkKey, credentials)
            d.addCallback(self._cbRequestAvatarId, credentials)
        d.addErrback(self._ebRequestAvatarId)
        return d

    def _ebRequestAvatarId(self, f):
        if not f.check(UnauthorizedLogin):
            twlog.msg(f)
            return failure.Failure(UnauthorizedLogin("unable to get avatar id"))
        return f

    def _cbRequestAvatarId(self, validKey, credentials):
        # Stop deprecation Warnings
        if not validKey:
            return failure.Failure(UnauthorizedLogin())
        if not credentials.signature:
            return failure.Failure(ValidPublicKey())
        else:
            try:
                pubKey = keys.Key.fromString(data = credentials.blob)
                if pubKey.verify(credentials.signature, credentials.sigData):
                    return credentials.username
            except: # any error should be treated as a failed login
                f = failure.Failure()
                twlog.err()
                return f
        return failure.Failure(UnauthorizedLogin())

    def checkKey(self, session, credentials):
        user = session.query(db.User).get(credentials.username)
        log.debug("User %s trying to authenticate", credentials.username)
        if not user:
            return False
        for pubKey in user.keys:
            if keys.Key.fromString(data=pubKey.key).blob() == credentials.blob:
                # Update last used timestamp of both the key and the user
                pubKey.update_stamp()
                user.last_used_key = pubKey
                session.commit()
                return True
        return False

    def authenticate(self, session, credentials):
        user = session.query(db.User).get(credentials.username)
        log.debug("User %s trying to authenticate", credentials.username)
        if not user:
            return defer.fail(UnauthorizedLogin("invalid username"))
        log.debug(user.authenticate(credentials.password))
        if user.authenticate(credentials.password):
            session.commit()
            session.close()
            return defer.succeed(credentials.username)
        return defer.fail(UnauthorizedLogin("unable to verify password"))

