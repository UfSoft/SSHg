# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from twisted.conch.ssh.session import SSHSessionProcessProtocol

from sshg import logger

log = logger.getLogger(__name__)

class MercurialSSHSessionProtocol(SSHSessionProcessProtocol):

    def processEnded(self, reason=None):
        SSHSessionProcessProtocol.processEnded(self, reason)
        if hasattr(self.transport, 'callbacks'):
            log.debug("Running processEnded Callbacks")
            self.transport.callbacks.callback(None)


