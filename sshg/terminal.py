# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import os.path
from inspect import getargspec
from twisted.conch.recvline import HistoricRecvLine
from sshg import logger, database as db, config

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
        HistoricRecvLine.__init__(self)
        self.avatar = avatar

    def motd(self):
        self.write(config.motd % COLORS)

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
        defaults = argspec[-1] or []
        log.debug("Separating args from kwargs")
        if defaults:
            args, kwargs = names[:-len(defaults)], names[-len(defaults):]
        else:
            args, kwargs = names, defaults
        log.debug('Args: %r KWArgs: %r Defaults len: %d', args, kwargs,
                  len(defaults))
        log.debug("Command: %s OurName: %s Action: %s", command, self.name, action)
        if (self.command and self.command.name == command) or \
            (self.name == command):
            command = None
        for idx, key in enumerate(kwargs):
            if isinstance(defaults[idx], bool):
                kwargs[idx] = "[%s <boolean>]" % key
            elif isinstance(defaults[idx], basestring) or \
                                                        defaults[idx] is None:
                kwargs[idx] = "[%s <string>]" % key
            elif isinstance(defaults[idx], int):
                kwargs[idx] = "[%s <integer>]" % key
        log.debug("Filter Above: %s", filter(None, [command, action]))
        usage = ' %%(green)sUsage%%(reset)s: %s %%(hilight)s%s' %(
            ' '.join(filter(None, [command, action])),
            ' '.join(["<%s>" % a for a in args] + kwargs)
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
                break
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
                runner = command or self
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
            if args and args[0] in runner.commands and cmd in runner.actions:
                new_cmd = args.pop(0)
                log.debug("Passing arguments to child command '%s': %r",
                          new_cmd, [cmd] + args)
                runner.commands[new_cmd].lineReceived(' '.join([cmd] + args))
                return
            elif cmd in runner.commands:
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
                d = defer.maybeDeferred(func, *args)
                d.addCallback(self.write)
                d.addErrback(self.commandExecutionFailed)
            else:
                self.write("No such command: '%s'" %
                           ' '.join(filter(None, [self.name, line])))
        self.nextLine()
        self.drawInputLine()

    def do_help(self, cmd='', format=None, extended=True):
        "Get help on a command."
        if cmd:
            log.debug("Issuing help for command %r", cmd)
            func = self.getCommandFunc(cmd)
            if not func and cmd in self.commands:
                log.debug("Calling regular help for command %s" % cmd)
                self.commands[cmd].do_help(format=format, extended=extended)
                return
            if func:
                doclines = []
                for line in func.__doc__.splitlines():
                    doclines.append(line.strip())

                log.debug("Found function %s for command %s", func, cmd)
                cmd_line = extended and ' '.join(doclines) or \
                     " %%(light-green)s%s%%(reset)s: %s" % (cmd,
                                                            ' '.join(doclines))
                if format and not extended:
                    cmd_line = format % (cmd, ' '.join(doclines))
                yield cmd_line % COLORS
                yield self.nextLine
                if extended:
                    usage = self.getFuncUsage(func, self.name, cmd)
                    yield usage
                    yield self.nextLine
                return


        if self.actions:
            yield "%(yellow)sCommands:" % COLORS
            yield self.nextLine
            longest = max([len(command) for command in self.actions])
            format = '%(light-green)s%%%%+%%ds%(reset)s: %%%%s' % COLORS
            for command in sorted(self.actions):
                yield self.do_help(command, format % (longest+1), extended=False)

        subcommands = self.commands.keys()
        if subcommands:
            log.debug("SubCommands: %r", subcommands)
            yield "%(yellow)sSub-Commands:" % COLORS
            yield self.nextLine
            longest = max([len(command) for command in subcommands])
            for command in subcommands:
                doclines = []
                for line in self.commands[command].__doc__.splitlines():
                    doclines.append(line.strip())
                yield format % (longest+2) % (command, ' '.join(doclines))
                yield self.nextLine

    def drawInputLine(self):
        if self.command:
            self.write(self.psc % self.command.name + ''.join(self.lineBuffer))
        else:
            self.write(self.ps + ''.join(self.lineBuffer))

    def keystrokeReceived(self, key_id, modifier):
        handler = self.keyHandlers.get(key_id)
        if handler is not None:
            handler()
        else:
            self.characterReceived(key_id, False)

    def commandExecutionFailed(self, exception):
        log.debug("Exception catched: %s", exception)
        if exception.type is TypeError:
            self.write('not enough arguments passed')
        else:
            self.write('command failed to execute')

    def write(self, lines):
        if not lines:
            log.debug('NOTHING TO WRITE. Got: %r', lines)
            return defer.SUCCESS
        log.debug("Received line to write: %r", lines)
        if isinstance(lines, unicode):
            lines = lines.encode('utf-8')
            lines = lines % COLORS
            log.debug("Line to actually Write: %r", lines)
        elif isinstance(lines, basestring):
            lines = lines % COLORS
        if hasattr(lines ,'__iter__'):
            for line in lines:
                if callable(line):
                    line()
                else:
                    self.write(line)
        elif isinstance(lines, defer.Deferred):
            lines.addCallbacks(self.write, self.commandExecutionFailed)
        else:
            d = defer.maybeDeferred(self.terminal.write, lines)
            d.addErrback(self.commandExecutionFailed)

class UserCommands(BaseAdminTerminal):
    """User Commands"""

    name = 'users'

    def do_list(self):
        """List Available Users."""
        yield " Available Users:"
        yield self.nextLine
        session = db.session()
        for username in session.query(db.User.username).all():
            log.debug("Found username: %s", username[0])
            yield u'  ' + username[0]
            yield self.nextLine

    def do_add(self, username, password, is_admin=False):
        """Add a new user."""
        session = db.session()
        user = db.User(username, password, bool(is_admin))
        session.add(user)
        session.commit()
        yield "User %s added" % username

    def do_details(self, username):
        """Show user details."""
        session = db.session()
        user = session.query(db.User).get(username)
        if not user:
            yield "User '%s' is not known" % username
            yield self.nextLine
            yield self.drawInputLine()
            return
        yield "%%(hilight)s   Username%%(reset)s: %s" % user.username
        yield self.nextLine
        yield "%%(hilight)s   Added On%%(reset)s: %s" % user.added_on
        yield self.nextLine
        yield "%%(hilight)s Last Login%%(reset)s: %s" % user.last_login
        yield self.nextLine
        yield "%%(hilight)s Locked Out%%(reset)s: %s" % user.locked_out
        yield self.nextLine
        yield "%%(hilight)s   Is Admin%%(reset)s: %s" % user.is_admin
        yield self.nextLine

    def do_delete(self, username):
        """Remove a user from database"""
        session = db.session()
        user = session.query(db.User).get(username)
        if not user:
            yield "User '%s' is not known" % username
            return
        session.delete(user)
        session.commit()
        yield "User %s deleted" % username

    def do_password(self, username, password):
        """Change user password"""
        session = db.session()
        user = session.query(db.User).get(username)
        if not user:
            yield "User '%s' is not known" % username
            return
        user.change_password(password)
        session.commit()
        yield "Password changed for user %s" % username



class BaseRepositoryCommands(BaseAdminTerminal):

    def _exists(self, session, reponame):
        return session.query(db.Repository).get(reponame)

class RepositoryUsersCommands(BaseRepositoryCommands):
    """Repository users commands."""
    name = 'repousers'

    def do_list(self, reponame):
        """List repository users."""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            yield  "A repository by the name of %s was not found." % reponame
            return
        log.debug(repo)
        yield " Repository Users:"
        yield self.nextLine
        if not repo.users:
            yield "Repository has no users."
            return
        for user in repo.users:
            yield "  %s" % user.username
            yield self.nextLine

class RepositoriesCommands(BaseRepositoryCommands):
    """Repositories Commands"""

    name = 'repos'

    commands = {'users': RepositoryUsersCommands()}

    def do_list(self):
        """List available repositories"""
        session = db.session()
        repos = session.query(db.Repository.name).all()
        if not repos:
            yield "No available repositories"
            return
        yield " Available Repositories:"
        yield self.nextLine
        for repo in repos:
            yield "  %s" % repo[0]
            yield self.nextLine

    def do_add(self, reponame, repopath, size=0, quota=0):
        """Add repository."""
        session = db.session()
        if self._exists(session, reponame):
            return "A repository by the name of %s already exists." % reponame
        if not os.path.isdir(repopath):
            return "The path to the repository '%s' does not exist." % repopath
        elif not os.path.isdir(os.path.join(repopath, '.hg')):
            return ("The path to the repository '%s' exists but does not "
                    "seem to be a valid mercurial repository.") % repopath
        repo = db.Repository(reponame, repopath, size, quota)
        session.add(repo)
        session.commit()
        return "Repository added.\n"

    def do_size(self, reponame):
        """Check the repository's current size"""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            return "A repository by the name of %s was not found." % reponame
        log.debug(repo)
        size = repo.get_size()
        return "Size: %s" % (size==0 and 'unlimited' or size)

    def do_quota(self, reponame, quota=0):
        """Check or set the repository's permitted quota"""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            return "A repository by the name of %s was not found." % reponame
        log.debug(repo)
        if quota:
            repo.quota = int(quota)
            session.commit()
            return "Repository quota updated to %s" % (repo.quota==0 and
                                                       'unlimited' or
                                                       repo.quota)
        return "Quota: %s" % (repo.quota==0 and 'unlimited' or repo.quota)

    def do_users(self, reponame, username=None):
        """Add a user to the repository. This user will be allowed to write
        to it"""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            yield  "A repository by the name of %s was not found." % reponame
            return
        log.debug(repo)
        if not username:
            if repo.users:
                yield " Repository Users:"
                yield self.nextLine
                for user in repo.users:
                    yield "  %s" % user.username
                    yield self.nextLine
            else:
                yield "Repository has no users."
            return
        user = session.query(db.User).get(username)
        if not user:
            yield "User %s is not known" % username
            return
        repo.users.append(user)
        session.commit()
        yield "User %s added to the %s repository users" % (username, reponame)


    def do_managers(self, reponame, manager=None):
        """Add a user as a manager to the repository. This user will be allowed
        to manage the repository"""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            return "A repository by the name of %s was not found." % reponame
        log.debug(repo)


class AdminTerminal(BaseAdminTerminal):
    commands = {
        'users': UserCommands(),
        'repos': RepositoriesCommands()
    }

    def do_exit(self):
        """Exit admin shell"""
        self.handle_CTRL_D()



    def do_password(self, password):
        """Change your password"""
        session = db.session()
        user = session.query(db.User).get(self.avatar.username)
        if not user:
            yield "User '%s' is not known" % self.avatar.username
            return
        user.change_password(password)
        session.commit()
        yield "Password changed for user %s" % self.avatar.username

    def do_whoami(self):
        """Tell's you who you are"""
        yield "You're %s!" % self.avatar.username
