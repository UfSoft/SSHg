# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from twisted.conch.recvline import HistoricRecvLine
from sshg import logger

log = logger.getLogger(__name__)


GREEN = '\x1b[32m'
LIGHT_GREEN = '\x1b[1;32m'
RED = '\x1b[31m'
LIGHT_RED = '\x1b[1;31m'
ORANGE = '\x1b[33m'
YELLOW = '\x1b[1;33m'
NORMAL_COLOR = '\x1b[0m'

COLORS = {
    'green': GREEN,
    'light-green': LIGHT_GREEN,
    'red': RED,
    'light-red': LIGHT_RED,
    'orange': ORANGE,
    'yellow': YELLOW,
    'reset': NORMAL_COLOR
}

from twisted.internet import defer


class BaseAdminTerminal(HistoricRecvLine):

    ps = '%(light-red)s[SSHg Admin]:%(reset)s ' % COLORS
    psc = '%(light-red)s[SSHg Admin %(light-green)s%%s%(light-red)s]:%(reset)s ' % COLORS
    command = name = terminal = None
    commands = {}

    def __init__(self, parent=None):
        if parent:
            self.terminal = parent.terminal
            self.connectionMade()
        for command, instance in self.commands.iteritems():
            self.commands[command] = instance(self)

    def motd(self):
        self.terminal.write(
            "%(green)s  Welcome to the SSHg console terminal. "
            "Type ? for help." % COLORS)
        self.nextLine()

    def nextLine(self):
        self.terminal.write(NORMAL_COLOR)
        self.terminal.nextLine()

    def initializeScreen(self):
        self.terminal.reset()
        self.motd()
        self.nextLine()
        self.terminal.write(self.ps)
        self.setInsertMode()

    def makeConnection(self, terminal):
        if self.terminal is None:
            self.terminal = terminal
        self.connectionMade()

    def connectionMade(self):
        HistoricRecvLine.connectionMade(self)
        self.keyHandlers.update({
            '\x03': self.handle_CTRL_C,
            '\x04': self.handle_CTRL_D,
        })
        publicMethods = filter(
            lambda funcname: funcname.startswith('do_'), dir(self))
        self.actions = [cmd.replace('do_', '', 1) for cmd in publicMethods]

    def terminalSize(self, width, height):
        # XXX - Clear the previous input line, redraw it at the new
        # cursor position
        self.terminal.eraseDisplay()
        self.terminal.cursorHome()
        self.width = width
        self.height = height
        self.motd()
        self.drawInputLine()

    def do_exit(self):
        """Exit admin shell"""
        self.terminal.loseConnection()
    handle_CTRL_C = handle_CTRL_D = do_exit

    def getMatchingCommands(self, prefix, command=None):
        log.debug("MatchingCommands -> Prefix: %r Command: %r", prefix, command)
        prefix = prefix.strip()
        if command:
            return [cmd for cmd in command.commands.keys()
                    if cmd.startswith(prefix)], [cmd for cmd in command.actions
                                                 if cmd.startswith(prefix)]

        return [cmd for cmd in self.commands.keys()
                if cmd.startswith(prefix)], [cmd for cmd in self.actions
                                             if cmd.startswith(prefix)]

        current = ''.join(self.lineBuffer).split()
        if self.lineBuffer[-1] == ' ':
            current.append('')
        log.debug('Current: %s', current)
        if len(current)==1:
            valid_commands = [cmd for cmd in self.commands.keys() +
                              self.actions if cmd.startswith(current[0])]
            if len(valid_commands) == 1:
                extend_buffer = valid_commands[0][len(current[0]):] + ' '
                self.lineBuffer.extend(extend_buffer)
                return extend_buffer
        else:
            if not current[1].strip():
                self.nextLine()
                self.write(' '.join(self.commands[current[0]].actions +
                                    self.commands[current[0]].commands.keys()))
                self.nextLine()
                self.drawInputLine()
            else:
                searcher = self.commands[current[0]]
                valid_commands = [cmd for cmd in searcher.commands.keys()
                                  if cmd.startswith(current[0])]
                if len(valid_commands) == 1:
                    extend_buffer = valid_commands[0][len(current[0]):] + ' '
                    self.lineBuffer.extend(extend_buffer)
                    return extend_buffer

    def handle_TAB(self):
        log.debug("Linebuffer: %s", self.currentLineBuffer())
        prefix = self.currentLineBuffer()[0]
        commands, actions = self.getMatchingCommands(prefix)
        log.debug("Matching: %r %r", commands, actions)
        if len(actions) > 1 or len(commands) > 1:
            self.nextLine()
            if len(actions) > 1:
                self.write('Commands: %s' % ', '.join(actions))
            if len(commands) > 1:
                self.write('Sub-Commands: %s' % ', '.join(commands))
            self.nextLine()
            self.drawInputLine()
        elif len(commands) == 1:
            command = commands[0]
            if command in self.commands:
                log.debug('Matched Command: %s', command)
                extend_buffer = command[self.lineBufferIndex:]
                self.lineBuffer.extend(extend_buffer)
                self.lineBufferIndex = len(self.lineBuffer)
                self.write(extend_buffer)
                prefix = prefix[len(command):].lstrip()
                if not prefix:
                    subcommands = self.commands[command].commands.keys()
                    subactions = self.commands[command].actions
                    if len(subactions) < 1 or len(subcommands) < 1:
                        self.nextLine()
                        if len(subactions) > 1:
                            self.write('Commands: %s' % ', '.join(subactions))
                        if len(subcommands) > 1:
                            self.write('Sub-Commands: %s' % ', '.join(subcommands))
                        self.nextLine()
                        self.drawInputLine()
                elif prefix:
                    log.debug('Sub Buffer: %r', prefix)
                    subcommands, subactions = self.getMatchingCommands(
                        prefix, self.commands.get(command, None))
                    log.debug("1: %r %r", subcommands, subactions)
                    if len(subactions) < 1 or len(subcommands) < 1:
                        self.nextLine()
                        if len(subactions) > 1:
                            self.write('Commands: %s' % ', '.join(subactions))
                        if len(subcommands) > 1:
                            self.write('Sub-Commands: %s' % ', '.join(subcommands))
                        self.nextLine()
                        self.drawInputLine()
        elif len(actions) == 1:
            extend_buffer = actions[0][self.lineBufferIndex:] + ' '
            self.lineBuffer.extend(extend_buffer)
            self.write(extend_buffer)
#        else:
#            self.write("No matches found for '%s'" % ''.join(self.lineBuffer))

    def getCommandFunc(self, command):
        return getattr(self, 'do_%s' % command, None)

    def switchToCommand(self, cmd):
        if cmd:
            self.command = self.commands[cmd]
            self.write("Issue the '..' command to go back")
            self.nextLine()
        else:
            self.command = cmd
        self.drawInputLine()

    def lineReceived(self, line):
        line = line.strip()
        if line:
            cmd_and_args = line.split()
            cmd = cmd_and_args[0]
            if cmd == '..':
                self.switchToCommand(None)
                return
            elif cmd == '?':
                cmd = 'help'
            args = cmd_and_args[1:]
            if self.command:
                runner = self.command
            else:
                runner = self
            if cmd in runner.commands:
                if not args:
                    self.switchToCommand(cmd)
                else:
                    runner.commands[cmd].lineReceived(' '.join(args))
                return
            func = runner.getCommandFunc(cmd)
            if callable(func):
                try:
                    self.write(defer.maybeDeferred(func, *args))
                except Exception, err:
                    self.write('Error: %s' % err)
            else:
                self.write("No such command: '%s'" % cmd)
        self.nextLine()
        self.drawInputLine()

    def do_help(self, cmd='', format=None):
        "Get help on a command. Usage: help command"
        if cmd:
            func = self.getCommandFunc(cmd)
            if func:
                cmd_line = " %%(green)s%s%%(reset)s: %s" % (cmd, func.__doc__)
                if format:
                    cmd_line = format % (cmd, func.__doc__)
                self.terminal.write(cmd_line % COLORS)
                self.terminal.nextLine()
                return

        publicMethods = filter(
            lambda funcname: funcname.startswith('do_'), dir(self))
        commands = [cmd.replace('do_', '', 1) for cmd in publicMethods]
        self.terminal.write("%(yellow)sCommands:" % COLORS)
        self.nextLine()
        longest = max([len(command) for command in commands])
        log.debug(publicMethods)
        format = '%(light-green)s%%%%+%%ds%(reset)s: %%%%s' % COLORS
        log.debug(repr(format))
        for command in sorted(commands):
            self.do_help(command, format % (longest+1))
        subcommands = self.commands.keys()
        if subcommands:
            self.terminal.write("%(yellow)sSub-Commands:" % COLORS)
            self.nextLine()
            longest = max([len(command) for command in subcommands])
            self.terminal.write(format % (longest+2) %
                                (command, self.commands[command].__doc__))

    def drawInputLine(self):
        if self.command:
            self.terminal.write(self.psc % self.command.name +
                                ''.join(self.lineBuffer))
        else:
            self.terminal.write(self.ps + ''.join(self.lineBuffer))

    def keystrokeReceived(self, keyID, modifier):
        m = self.keyHandlers.get(keyID)
        if m is not None:
            m()
        else:
            self.characterReceived(keyID, False)

    def write(self, line):
        if isinstance(line, defer.Deferred):
            line.addCallback(self.write)
        else:
            self.terminal.write(line)

class UserCommands(BaseAdminTerminal):
    """User Commands"""

    name = 'users'

    def do_list(self):
        """List Available Users"""
        self.terminal.write('Available Users:')
        self.nextLine()
        from sshg import database as db
        session = db.session()
        for username in session.query(db.User.username).all():
            log.debug(username)
            self.terminal.write('  ' + username[0].encode('utf-8'))
            self.terminal.nextLine()

class AdminTerminal(BaseAdminTerminal):

    def connectionMade(self):
        BaseAdminTerminal.connectionMade(self)
        self.commands = {
            'users': UserCommands(self),
            'foo': UserCommands(self),
            'foobar': UserCommands(self)
        }
