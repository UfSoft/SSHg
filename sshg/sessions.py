# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.sessions
    ~~~~~~~~~~~~~

    This module is responsible for the used ssh sessions.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import shlex
import simplejson
from os import environ
from twisted.conch.manhole_ssh import TerminalSession
from twisted.conch.ssh import session, channel
from twisted.conch.ssh.connection import EXTENDED_DATA_STDERR
from twisted.conch.error import NotEnoughAuthentication
from twisted.internet import reactor, defer
from twisted.python import components
from sshg import logger, database as db
from sshg.terminal import AdminTerminal

log = logger.getLogger(__name__)

class StopProcessing(Exception):
    """Exception for when we prohibit something"""

class FixedSSHSession(session.SSHSession):
    in_counter = 0
    out_counter = 0

    reponame = None
    callbacks = defer.Deferred()

    def _errorCallBack(self, failure):
        if failure.check(StopProcessing):
            self.writeExtended(EXTENDED_DATA_STDERR, "FOO")
            self.loseConnection()
            return
        log.exception(failure)

    def loseConnection(self):
        log.debug("On loseConnection")
        if self.client and self.client.transport:
            # Only call loseConnection if we have a transport set up
            self.client.transport.loseConnection()
        channel.SSHChannel.loseConnection(self)

    def closeReceived(self):
        log.debug("on closeReceived()")
        session.SSHSession.closeReceived(self)

    def closed(self):
        log.debug("on closed()")
        if self.reponame:
            self.callbacks.addCallback(self._update_database)
            self.callbacks.addErrback(self._errorCallBack)
            if not self.callbacks.called:
                self.callbacks.callback(None)
        session.SSHSession.closed(self)

    @defer.inlineCallbacks
    def dataReceived(self, data):
        self.in_counter += yield len(data)
        yield log.debug("Current In Counter: %s", self.in_counter)
        if not self.client:
            yield self.conn.sendClose(self)
            self.buf += yield data
        if self.client.transport:
            # Only write if we have a transport set up
            yield self.client.transport.write(data)

    @defer.inlineCallbacks
    def write(self, data):
        self.out_counter += yield len(data)
#        yield log.debug("Current Out Counter: %s", self.out_counter)
        yield session.SSHSession.write(self, data)

    @defer.inlineCallbacks
    def writeExtended(self, dataType, data):
        yield log.debug("EXTENDED - Current Out Counter: %s  DataType: %r  "
                        "Data: %r", self.out_counter, dataType, data)
        yield session.SSHSession.writeExtended(self, dataType, data)

    def _update_database(self, previous_result):
        session = db.session()
        repo = session.query(db.Repository).get(self.reponame)
        if not repo:
            log.error("Could not found repo %r on database", self.reponame)
        repo.calculate_size()
        repo.traffic.append(db.RepositoryTraffic(self.in_counter,
                                                 self.out_counter))
        try:
            session.commit()
        except Exception, err:
            log.error("Rolling back session: %r", err)
            session.rollback()


class MercurialSession(TerminalSession):

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
        log.debug(protocol)
        d = defer.maybeDeferred(db.session)
        d.addCallback(self._cbExecCommand, protocol, cmd)
        d.addErrback(self._ebExecCommand, protocol)
        return d

    def _cbExecCommand(self, session, protocol, cmd):
        args = shlex.split(cmd)
        if args.pop(0) != 'hg':
            log.warning("User %s trying to run a command(%s) other than a "
                        "mercurial repository", self.avatar.username, cmd)
            raise StopProcessing("Command not allowed!")

        # Discard -R
        args.pop(0)

        # Get repository name
        repository_name = args.pop(0)

        # Make avatar load stuff from database
        user = session.query(db.User).get(self.avatar.username)
        log.debug("User: %r  Reponame: %r", user, repository_name)
        if user.is_admin:
            repo = session.query(db.Repository).get(repository_name)
        else:
            dbfilter = db.Repository.name==repository_name
            repo = user.repos.filter(dbfilter).first()
            if not repo:
                repo = user.manages.filter(dbfilter).first()

        if not repo:
            log.error("Repository %s not found!", repository_name)
            raise StopProcessing("Repository not found!")

        log.debug("Got Repository: %r", repo)

        if repo.size > repo.quota:
            log.error("Repository %s over quota.", repo.name)
            raise StopProcessing("Repository over quota.")

        # Set repository name in ssh's session channel so that
        # database updates can occur
        protocol.session.reponame = repository_name

        serve = args.pop(0)
        stdio = args.pop(0)
        if serve != 'serve' or stdio != '--stdio':
            # Client is not trying to run an HG repository
            raise NotEnoughAuthentication("Repository not found")

        log.debug("Are there any args left? %s", args)

        repository_path = str(repo.path)
        process_args = ['hg', '-R', repository_path, serve, stdio]
        #process_args.append('--debug')

        self.hg_process_pid = reactor.spawnProcess(
            processProtocol=protocol,
            executable='hg', args=process_args,
            path=repository_path,
            env = {'SSHg.ALLOW': simplejson.dumps([]),
                   'SSHg.DENY': simplejson.dumps([]),
                   'SSHg.SOURCES': simplejson.dumps([]),
                   'SSHg.USERNAME': self.avatar.username,
                   'PATH': environ.get('PATH')
            }
        )
        # Above, one could try instead to open the mercurial repository
        # ourselves and pipe data back and forth, but, twisted can do that
        # for us :)
        # I think I should let this for mercurial itself, whenever mercurial
        # changed it's sshserver code, we would have to change the twisted
        # protocol implementing it


    def _ebExecCommand(self, failure, protocol):
        if failure.check(StopProcessing):
            message = "SSHg -> %s\n\r" % failure.value.message.strip()
            protocol.session.writeExtended(EXTENDED_DATA_STDERR, message)
            protocol.loseConnection()
            return
        log.exception(failure)

    def eofReceived(self):
        if self.hg_process_pid:
            self.hg_process_pid.loseConnection()
            self.hg_process_pid = None
    closed = eofReceived

    def openShell(self, protocol):
        log.warning("Disallowed opening shell for %s", self.avatar.username)
        protocol.loseConnection()

    def getPtyOwnership(self):
        log.debug("getPtyOwnership")
        TerminalSession.getPtyOwnership(self)

    def setModes(self):
        log.debug("setModes")
        TerminalSession.setModes(self)


class MercurialAdminSession(MercurialSession):
    width = 80
    height = 24

    def openShell(self, protocol):
        self.transportFactory(
            protocol,
            self.chainedProtocolFactory(AdminTerminal, avatar=self.avatar),
            self.avatar, self.width, self.height)
