# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from inspect import getargspec
from twisted.conch.recvline import HistoricRecvLine
from sshg import logger, database as db

log = logger.getLogger(__name__)


GREEN = '\x1b[32m'
LIGHT_GREEN = '\x1b[1;32m'
RED = '\x1b[31m'
LIGHT_RED = '\x1b[1;31m'
ORANGE = '\x1b[33m'
YELLOW = '\x1b[1;33m'
NORMAL_COLOR = '\x1b[0m'
HILIGHT = '\x1b[1m'

COLORS = {
    'green': GREEN,
    'light-green': LIGHT_GREEN,
    'red': RED,
    'light-red': LIGHT_RED,
    'orange': ORANGE,
    'yellow': YELLOW,
    'reset': NORMAL_COLOR,
    'hilight': HILIGHT
}

from twisted.internet import defer


class BaseAdminTerminal(HistoricRecvLine):

    ps = '%(light-red)s[SSHg Admin]:%(reset)s ' % COLORS
    psc = '%(light-red)s[SSHg Admin %(light-green)s%%s%(light-red)s]:%(reset)s ' % COLORS
    command = parent = name = terminal = None
    commands = {}

    def __init__(self, avatar=None):
        self.avatar = avatar
        HistoricRecvLine.__init__(self)

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
        for instance in self.commands.itervalues():
            log.debug(instance)
            instance.makeConnection(terminal)
            instance.connectionMade()

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

    def handle_CTRL_D(self):
        """Exit admin shell"""
        self.terminal.loseConnection()
    handle_CTRL_C = handle_CTRL_D

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

    def getFuncUsage(self, func, command, action):
        log.debug('Func: %s', func)
        log.debug('ArgSpec: %s', getargspec(func))

        argspec = getargspec(func)
        names = argspec[0]
        names.pop(0)
        defaults = argspec[-1]
        if defaults:
            log.debug("Got Defaults, separating args from kwargs")
            args, kwargs = names[:-len(defaults)], names[-len(defaults):]
        else:
            args, kwargs = names, ()
        log.debug('Args: %r KWArgs: %r Defaults len: %d', args, kwargs,
                  len(defaults or ()))
        if command:
            usage = ' %%(green)sUsage%%(reset)s: %s %s %%(hilight)s%s %s' %(
                command or '', action,
                ' '.join(["<%s>" % a for a in args]),
                ' '.join(["[%s]" % k for k in kwargs])
            )
        else:
            usage = ' %%(green)sUsage%%(reset)s: %s %%(hilight)s%s %s' %(
                action, ' '.join(["<%s>" % a for a in args]),
            ' '.join(["[%s]" % k for k in kwargs])
            )
        return usage % COLORS

    def handle_TAB(self):
        log.debug("Linebuffer: %s", self.currentLineBuffer())
        buff = self.currentLineBuffer()[0].split()
        command = self.command
        action = None
        while buff:
            prefix = buff.pop(0)
            log.debug('Current Prefix: %r', prefix)
            commands, actions = self.getMatchingCommands(prefix, command)
            log.debug("Matching: %r %r", commands, actions)
            if len(actions) > 1 or len(commands) > 1:
                self.nextLine()
                self.write("%%(hilight)s%s%%(reset)s" %
                           ' '.join(actions + commands) % COLORS)
                self.nextLine()
                self.drawInputLine()
            elif len(commands) == 1:
                if commands[0] in self.commands:
                    log.debug('Matched Command: %s', commands[0])
                    extend_buffer = commands[0][len(prefix):]
                    self.lineBuffer.extend(extend_buffer)
                    self.lineBufferIndex = len(self.lineBuffer)
                    self.write(extend_buffer)
                    command = self.commands[commands[0]]
                    continue
            elif len(actions) == 1:
                log.debug('Matched Action: %s', actions[0])
                extend_buffer = actions[0][len(prefix):]
                self.lineBuffer.extend(extend_buffer)
                self.lineBufferIndex = len(self.lineBuffer)
                self.write(extend_buffer)
                runner = command or self
                action = actions[0]
                continue
        else:
            log.debug('No more line buffer')
            if action:
                runner = command or self.command or self
                if action == 'help':
                    log.debug('On help returning available actions for %r',
                              runner.__class__)
                    output = ' '.join(runner.commands.keys() + runner.actions)
                    self.nextLine()
                    self.write("%%(hilight)s%s%%(reset)s" % output % COLORS)
                    self.nextLine()
                    self.drawInputLine()
                    return
                func = getattr(runner, 'do_%s' % action)
                usage = self.getFuncUsage(func, runner.name, action)
                self.nextLine()
                self.write(usage)
                self.nextLine()
                self.drawInputLine()
            elif not action:
                runner = command or self
                self.nextLine()
                output = ' '.join(runner.commands.keys() + runner.actions)
                self.write("%%(hilight)s%s%%(reset)s" % output % COLORS)
                self.nextLine()
                self.drawInputLine()

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
        log.debug("Received line on %s: %r", self.__class__.__name__, line)
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
                    log.debug("Passing arguments to child command '%s': %r",
                              cmd, args)
                    runner.commands[cmd].lineReceived(' '.join(args))
                return
            func = runner.getCommandFunc(cmd)
            log.debug("Discovered function: %s", func)
            if callable(func):
                def error(exception):
                    log.debug("Exception catched: %s", exception)
                    if exception.type is TypeError:
                        self.write('not enough arguments passed')
                    else:
                        self.write('command failed to execute')
                d = defer.maybeDeferred(func, *args)
                d.addCallback(self.write)
                d.addErrback(error)
            else:
                self.write("No such command: '%s'" %
                           ' '.join(filter(None, [self.name, line])))
        self.nextLine()
        self.drawInputLine()

    def do_help(self, cmd='', format=None, extended=True):
        "Get help on a command. Usage: help command"
        if cmd:
            func = self.getCommandFunc(cmd)
            if not func:
                func = self.commands.get(cmd, None)
            if func:
                if extended:
                    cmd_line = func.__doc__
                else:
                    cmd_line = " %%(light-green)s%s%%(reset)s: %s" % (
                                                            cmd, func.__doc__)
                    if format:
                        cmd_line = format % (cmd, func.__doc__)
                self.terminal.write(cmd_line % COLORS)
                self.nextLine()
                if extended:
                    usage = self.getFuncUsage(func, self.name, cmd)
                    self.write(usage)
                    self.nextLine()
                return

        if self.actions:
            self.terminal.write("%(yellow)sCommands:" % COLORS)
            self.nextLine()
            longest = max([len(command) for command in self.actions])
            format = '%(light-green)s%%%%+%%ds%(reset)s: %%%%s' % COLORS
            for command in sorted(self.actions):
                self.do_help(command, format % (longest+1), extended=False)

        subcommands = self.commands.keys()
        if subcommands:
            log.debug("SubCommands: %r", subcommands)
            self.terminal.write("%(yellow)sSub-Commands:" % COLORS)
            self.nextLine()
            longest = max([len(command) for command in subcommands])
            for command in subcommands:
                self.do_help(command, format % (longest+2), extended=False)

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
        session = db.session()
        for username in session.query(db.User.username).all():
            log.debug(username)
            self.terminal.write('  ' + username[0].encode('utf-8'))
            self.terminal.nextLine()

    def do_add(self, username, password, is_admin=False):
        """Add a new user"""
        session = db.session()
        user = db.User(username, password, bool(is_admin))
        session.add(user)
        session.commit()
        self.write("User %s added" % username)

    def do_details(self, username):
        """Show user details"""
        session = db.session()
        user = session.query(db.User).get(username)
        if not user:
            self.write("User '%s' is not known" % username)
            self.nextLine()
            self.drawInputLine()
            return
        w = lambda txt: (self.write(txt % COLORS), self.nextLine())
        w("%%(hilight)s   Username%%(reset)s: %s" %
          user.username.encode('utf-8'))
        w("%%(hilight)s   Added On%%(reset)s: %s" % user.added_on)
        w("%%(hilight)s Last Login%%(reset)s: %s" % user.last_login)
        w("%%(hilight)s Locked Out%%(reset)s: %s" % user.locked_out)
        w("%%(hilight)s   Is Admin%%(reset)s: %s" % user.is_admin)

    def do_delete(self, username):
        """Remove a user from database"""
        session = db.session()
        user = session.query(db.User).get(username)
        if not user:
            self.write("User '%s' is not known" % username)
            return
        session.delete(user)
        session.commit()
        self.write("User %s deleted" % username)

    def password(self, username, password):
        """Change user password"""
        session = db.session()
        user = session.query(db.User).get(username)
        if not user:
            self.write("User '%s' is not known" % username)
            return
        user.change_password(password)
        session.commit()
        self.write("Password changed for user %s" % username)

class AdminTerminal(BaseAdminTerminal):
    commands = {
        'users': UserCommands()
    }

    def do_exit(self):
        """Exit admin shell"""
        self.handle_CTRL_D()



    def do_password(self, password):
        """Change your password"""
        session = db.session()
        user = session.query(db.User).get(self.avatar.username)
        if not user:
            self.write("User '%s' is not known" % self.avatar.username)
            return
        user.change_password(password)
        session.commit()
        self.write("Password changed for user %s" % self.avatar.username)

    def do_whoami(self):
        """Tell's you who you are"""
        self.write("You're %s!" % self.avatar.username)
