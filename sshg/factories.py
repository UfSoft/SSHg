# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.factories
    ~~~~~~~~~~~~~~

    This module is responsible the service factories.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.conch.ssh import factory, keys
from sshg import config, logger

log = logger.getLogger(__name__)

class MercurialReposFactory(factory.SSHFactory):

    def __init__(self, realm, portal):
        realm.factory = portal.factory = self
        self.realm = realm
        self.portal = portal

        self._privateKey = keys.Key.fromString(open(config.private_key).read())
        self._publicKey = self._privateKey.public()

    def getPublicKeys(self):
        return {'ssh-rsa': self._publicKey}

    def getPrivateKeys(self):
        return {'ssh-rsa': self._privateKey}

    def __repr__(self):
        return '<Mercurial Repositories Factory from %s>' % self.__class__

