# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.sessions
    ~~~~~~~~~~~~~

    This module is responsible for the used ssh sessions.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.conch.ssh import session, channel
from twisted.internet import reactor
from twisted.python import log
from zope.interface import implements


class FixedSSHSession(session.SSHSession):
    def loseConnection(self):
        if self.client and self.client.transport:
            # Only call loseConnection if we have a transport set up
            self.client.transport.loseConnection()
        channel.SSHChannel.loseConnection(self)

    def dataReceived(self, data):
        if not self.client:
            self.conn.sendClose(self)
            self.buf += data
        if self.client.transport:
            # Only write if we have a transport set up
            self.client.transport.write(data)

class MercurialSession(object):
    implements(session.ISession)

    hg_process_pid = None

    def __init__(self, avatar):
        log.msg("Initiated Mercurial Session: %s" % avatar.username)
        self.avatar = avatar
        self.factory = avatar.factory

    def getPty(self, term, windowSize, attrs):
        print "getPTY"
        pass

    def windowChanged(self, newWindowSize):
        print "windowChanged"
        pass


    def execCommand(self, protocol, cmd):
        args = cmd.split()
        if args.pop(0) != 'hg':
            protocol.loseConnection()
            return

        # Discard -R
        args.pop(0)

        # Get repository name
        repository_name = args.pop(0)

        # Make avatar load stuff from database
        repo = self.avatar.user.getRepo(repository_name)

        if args.pop(0) != 'serve' or args.pop(0) != '--stdio' or repo is None:
            # Client is not trying to run an HG repository
            protocol.loseConnection()
            return

        print "Are there any args left?", args

        repository_path = str(repo.path)

        process_args = ['hg', '-R', repository_path, 'serve', '--stdio']
        #process_args.append('--debug')
        self.hg_process_pid = reactor.spawnProcess(processProtocol = protocol,
                                                   executable = 'hg',
                                                   args = process_args,
                                                   path = repository_path)
        # Above, one could try instead to open the mercurial repository
        # ourselves and pipe data back and forth, but, twisted can do that
        # for us ;)

    def eofReceived(self):
        if self.hg_process_pid:
            self.hg_process_pid.loseConnection()
            self.hg_process_pid = None

    def closed(self):
        if self.hg_process_pid:
            self.hg_process_pid.loseConnection()
            self.hg_process_pid = None

    def openShell(self, transport):
        transport.loseConnection()

    def getPtyOwnership(self):
        print "getPtyOwnership"

    def setModes(self):
        print "setModes"
