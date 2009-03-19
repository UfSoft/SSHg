# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.factories
    ~~~~~~~~~~~~~~

    This module is responsible the service authentication chekers.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.conch.error import ValidPublicKey
from twisted.conch.ssh import keys
from twisted.cred.error import UnauthorizedLogin
from twisted.python import failure, log

from sshg.database import User, require_session

class MercurialPublicKeysDB(SSHPublicKeyDatabase):

    @require_session
    def checkKey(self, credentials, session=None):
        user = session.query(User).get(credentials.username)
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
                log.err()
                return f
        return failure.Failure(UnauthorizedLogin())
