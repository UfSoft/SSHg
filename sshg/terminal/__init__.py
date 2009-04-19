# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import shlex
from os.path import commonprefix
from twisted.conch.recvline import HistoricRecvLine
from twisted.internet import defer

from sshg import config, logger
from sshg.terminal.commands import CommandNotFound
from sshg.terminal.commands.root import RootAdminCommands

log = logger.getLogger(__name__)

GREEN = '\x1b[32m'
LIGHT_GREEN = '\x1b[1;32m'
RED = '\x1b[31m'
LIGHT_RED = '\x1b[1;31m'
ORANGE = '\x1b[0;33m'
YELLOW = '\x1b[1;33m'
NORMAL_COLOR = '\x1b[0m'
HILIGHT = '\x1b[1m'
BLUE = '\x1b[1;34m'
LIGHT_BLUE = '\x1b[1;34m'

COLORS = {
    'G'  : GREEN,
    'LG' : LIGHT_GREEN,
    'R'  : RED,
    'LR' : LIGHT_RED,
    'O'  : ORANGE,
    'Y'  : YELLOW,
    'RST': NORMAL_COLOR,
    'HI' : HILIGHT,
    'B'  : BLUE,
    'LB' : LIGHT_BLUE,

}

class AdminTerminal(HistoricRecvLine):
    psc = '%%(LB)s[SSHg Admin %%(LG)s%s%%(LB)s]:%%(RST)s '
    defaultCommand = None
    selectedCommand = None

    def __init__(self, avatar=None):
        HistoricRecvLine.__init__(self)
        self.avatar = avatar

    def nextLine(self):
        self.terminal.write(NORMAL_COLOR)
        self.terminal.nextLine()

    def initializeScreen(self):
        self.terminal.reset()
        self.motd()
        self.nextLine()
        self.drawInputLine()
        self.setInsertMode()

    def makeConnection(self, terminal):
        self.terminal = terminal
        self.defaultCommand = RootAdminCommands(terminal=self)
        self.selectedCommand = self.defaultCommand
        self.connectionMade()

    def connectionMade(self):
        HistoricRecvLine.connectionMade(self)
        self.keyHandlers.update({
            '\x03': self.handle_CTRL_C,
            '\x04': self.handle_CTRL_D,
        })

    def loseConnection(self):
        """Exit administration shell"""
        if self.defaultCommand:
            del self.defaultCommand
            self.defaultCommand = None
        self.terminal.loseConnection()
    handle_CTRL_C = handle_CTRL_D = loseConnection

    def terminalSize(self, width, height):
        # XXX - Clear the previous input line, redraw it at the new
        # cursor position
        self.terminal.eraseDisplay()
        self.terminal.cursorHome()
        self.width = width
        self.height = height
        self.motd()
        self.drawInputLine()

    def drawInputLine(self):
        ps =  self.selectedCommand is self.defaultCommand and '' or '/'
        ps += '/'.join(filter(None, self.selectedCommand.cmdpath()))
        log.debug("Parts: %r PS: %r", list(self.selectedCommand.cmdpath()), ps)
        self.write(self.psc % ps + ''.join(self.lineBuffer))

    def keystrokeReceived(self, key_id, modifier):
        handler = self.keyHandlers.get(key_id)
        if handler is not None:
            handler()
        else:
            self.characterReceived(key_id, False)

    def lineReceived(self, line):
        log.debug("Received line on %s: %r", self.__class__.__name__, line)
        try:
            args = shlex.split(line)
        except ValueError, err:
            # No closing commas
            self.write("%%(LR)sERROR%%(RST)s: %s" % err)
            self.nextLine()
            self.drawInputLine()
            return
        action = None
        command = self.selectedCommand
        while True:
            log.debug("Current Command: %r  Current Action: %r  "
                      "Remaining Args: %r", command, action, args)
            if not args:
                break
            arg = args.pop(0)
            log.debug("Processing arg: %r", arg)
            if arg == '/' and not args:
                # Switch to root command
                self.switchCommand(self.defaultCommand)
                self.nextLine()
                self.drawInputLine()
                return
            elif arg == '..':
                # Switch to parent command
                self.switchCommand(self.selectedCommand.parent)
                self.nextLine()
                self.drawInputLine()
                return
            elif arg == '?':
                arg = 'help'

            if arg in command.commands:
                if not args and action != 'help':
                    # Issue a switch command
                    log.debug("Issue switch command to %r", command)
                    self.switchCommand(command.commands[arg])
                    self.nextLine()
                    self.drawInputLine()
                    return
                elif not args and action == 'help':
                    # Requiring help for an action
                    args.append(arg)
                    break
                else:
                    # Keep looping
                    log.debug("Remaining args: %r", args)
                    command = command.commands[arg]
                    log.debug("Switched to command: %r Remaining Args: %r",
                              command, args)
                    continue
            elif action == 'help' and arg in command.actions and not args:
                # Issue help for an action
                log.debug("Issue help for action %s on command %s",
                          action, command)
                args.append(arg)
                break
            elif arg in command.actions:
                # Store current found action
                action = arg
            elif arg not in command.actions:
                # No more actions to look for, insert the popped argument
                # which will be used on the found action
                args.insert(0, arg)
                break
        log.debug("Command: %r  Action: %r  Args: %r",
                  command, action, args)
        func = command.get_action(action)
        if callable(func):
            log.debug("Discovered function: %s Remaining Args: %r",
                      func, args)
            d = defer.maybeDeferred(func, *args)
            d.addCallback(self.write).addErrback(self.commandExecutionFailed)
        else:
            self.write("No such command: '%s'" % line)
        self.nextLine()
        self.drawInputLine()

    # Custom Functions
    def switchCommand(self, command):
        if command is not self.defaultCommand:
            self.write("%(O)sIssue the command %(Y)s..%(O)s to go back "
                       "or %(Y)s/%(O)s to go to the root command.")
        self.selectedCommand = command

    def write(self, lines):
        #log.debug("<%s> Received line to write: %r",
        #          self.__class__.__name__, lines)
        if not lines:
        #    log.debug('NOTHING TO WRITE.')
            return defer.SUCCESS
        if isinstance(lines, unicode):
            lines = lines.encode('utf-8')
            lines = lines % COLORS
            log.debug("Line to actually Write: %r", lines)
        elif isinstance(lines, basestring):
            lines = lines % COLORS
        if hasattr(lines, '__iter__'):
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

    def commandExecutionFailed(self, exception):
        log.debug("Exception catched: %s", exception)
        if exception.type is TypeError:
            self.write('wrong number of arguments passed')
        elif exception.type is CommandNotFound:
            self.write("No such command: '%s'" % exception.value)
        else:
            self.write('command failed to execute')

    def motd(self):
        self.write(config.motd)

    def handle_TAB(self):
        log.debug("Linebuffer: %s", self.currentLineBuffer())
        buff = shlex.split(self.currentLineBuffer()[0])
        command = self.selectedCommand
        log.debug("CMD: %r", command)
        action = None
        while buff:
            prefix = buff.pop(0)
            log.debug('Current Prefix: %r', prefix)
            log.debug('Current Command: %r', command)
            log.debug('Current Action: %r', action)
            if not buff and self.lineBuffer[-1] == ' ':
                prefix += ' '
            commands, actions = command.get_matches(prefix, command)
            log.debug("Matching: %r %r", commands, actions)
            if len(actions) > 1 or len(commands) > 1:
                extended_buffer = commonprefix(actions + commands)[len(prefix):]
                self.lineBuffer.extend(extended_buffer)
                self.lineBufferIndex = len(self.lineBuffer)
                self.nextLine()
                self.write("%%(HI)s%s%%(RST)s" % ' '.join(actions + commands))
                self.nextLine()
                self.drawInputLine()
                break
            elif len(commands) == 1:
                if commands[0] in command.commands:
                    log.debug('Matched Command: %s', commands[0])
                    extend_buffer = commands[0][len(prefix):]
                    self.lineBuffer.extend(extend_buffer)
                    self.lineBufferIndex = len(self.lineBuffer)
                    self.write(extend_buffer)
                    command = command.commands[commands[0]]
                    continue
            elif len(actions) == 1:
                if ''.join(self.lineBuffer).endswith('help') or \
                   ''.join(self.lineBuffer).endswith('help '):
                    show_break = False
                else:
                    show_break = True
                log.debug('Matched Action: %s', actions[0])
                log.debug("Should break: %r", show_break)
                extend_buffer = actions[0][len(prefix):]
                self.lineBuffer.extend(extend_buffer)
                self.lineBufferIndex = len(self.lineBuffer)
                self.write(extend_buffer)
                action = actions[0]
                if not show_break:
                    break
                else:
                    continue
        else:
            log.debug('No more line buffer')
            if action:
                if action == 'help':
                    log.debug('On help returning available actions for %r',
                              command.__class__)
                    output = ' '.join(command.commands.keys() +
                                      command.actions)
                    self.nextLine()
                    self.write("%%(HI)s%s%%(RST)s" % output)
                    self.nextLine()
                    self.drawInputLine()
                    return
                func = getattr(command, 'do_%s' % action)
                usage = command.get_usage(func, command.cmdname, action)
                self.nextLine()
                self.write(usage)
                self.nextLine()
                self.drawInputLine()
            elif not action:
                self.nextLine()
                output = ' '.join(command.commands.keys() + command.actions)
                self.write("%%(HI)s%s%%(RST)s" % output)
                self.nextLine()
                self.drawInputLine()

