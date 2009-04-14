# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.sessions
    ~~~~~~~~~~~~~

    This module is responsible for the used ssh sessions.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.conch.insults.insults import ServerProtocol
from twisted.conch.manhole_ssh import (TerminalSessionTransport as TSP,
                                       TerminalSession, _Glue)
from twisted.conch.ssh import session, channel
from twisted.internet import reactor
from twisted.python import components
from sshg import logger
from sshg.terminal import AdminTerminal

log = logger.getLogger(__name__)

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

class TerminalSessionTransport(TSP):
    def __init__(self, proto, chainedProtocol, avatar, width, height):
        self.proto = proto
        self.avatar = avatar
        self.chainedProtocol = chainedProtocol

        session = self.proto.session

        self.proto.makeConnection(
            _Glue(write=self.chainedProtocol.dataReceived,
                  loseConnection=lambda: avatar.conn.sendClose(session),
                  avatar=avatar, name="SSHg Proto Transport"))

        def loseConnection():
            self.proto.loseConnection()

        self.chainedProtocol.makeConnection(
            _Glue(write=self.proto.write,
                  loseConnection=loseConnection,
                  avatar=avatar, name="SSHG Chained Proto Transport"))

        # XXX TODO
        # chainedProtocol is supposed to be an ITerminalTransport,
        # maybe.  That means perhaps its terminalProtocol attribute is
        # an ITerminalProtocol, it could be.  So calling terminalSize
        # on that should do the right thing But it'd be nice to clean
        # this bit up.
        self.chainedProtocol.terminalProtocol.terminalSize(width, height)

class MercurialSession(TerminalSession):
    #implements(session.ISession)

    hg_process_pid = None

    def __init__(self, original, avatar):
        log.debug("Initiated Mercurial Session: %s" % avatar.username)
        components.Adapter.__init__(self, original)
        self.avatar = avatar
        #self.factory = avatar.factory

    def getPty(self, term, windowSize, attrs):
        log.debug("getPTY")
        TerminalSession.getPty(self, term, windowSize, attrs)

    def windowChanged(self, newWindowSize):
        log.debug("windowChanged")
        TerminalSession.windowChanged(self, newWindowSize)


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

        log.debug("Are there any args left? %s", args)

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
        log.debug("getPtyOwnership")
        TerminalSession.getPtyOwnership(self)

    def setModes(self):
        log.debug("setModes")
        TerminalSession.setModes(self)


class MercurialAdminSession(MercurialSession):
    width = 80
    height = 24

    transportFactory = TerminalSessionTransport
    chainedProtocolFactory = ServerProtocol


    def openShell(self, transport):
        self.transportFactory(transport,
                              self.chainedProtocolFactory(AdminTerminal),
                              self.avatar, self.width, self.height)
