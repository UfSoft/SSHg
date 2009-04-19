# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from inspect import getargspec
from sshg import logger, database as db

log = logger.getLogger(__name__)

__all__ = ['BaseCommand', 'logger', 'db']

class CommandNotFound(Exception):
    """Exception raise for not found commands"""

class BaseCommand(object):
    """Base Terminal Commands Interface"""
    cmdname = None
    commands = None
    __commands__ = []

    def __init__(self, parent=None, terminal=None):
        self.parent = parent
        self.terminal = terminal
        self.commands = {}

        # PowerUp child commands
        for klass in self.__commands__:
            self.commands[klass.cmdname] = klass(parent=self, terminal=terminal)

    def cmdpath(self):
        if self.parent:
            for cmdname in self.parent.cmdpath():
                yield cmdname
        yield self.cmdname

    @property
    def actions(self):
        """Return the command actions."""
        return [cmd.replace('do_', '', 1) for cmd in
                filter(lambda funcname: funcname.startswith('do_'), dir(self))]

    def get_matches(self, prefix, command=None):
        """Get the actions and/or sub-commands matching the passed prefix."""
        log.debug("MatchingCommands -> Prefix: %r Command: %r", prefix, command)
        command = command or self
        commands = [cmd for cmd in command.commands.keys()
                    if cmd.startswith(prefix)]
        actions = [cmd for cmd in command.actions if cmd.startswith(prefix)]
        log.debug("Returning - Commands: %r  Actions: %r", commands, actions)
        return commands, actions

    def get_usage(self, func, command, action):
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
        log.debug("Command: %s OurName: %s Action: %s", command,
                  self.cmdname, action)
        if self.cmdname == command:
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
        usage = ' %%(G)sUsage%%(RST)s: %s %%(HI)s%s' % (
            ' '.join(filter(None, [command, action])),
            ' '.join(["<%s>" % a for a in args] + kwargs)
        )
        return usage

    def get_doc(self, klass_or_func):
        if klass_or_func.__doc__:
            for line in klass_or_func.__doc__.splitlines():
                yield line.strip()
        yield ''

    def get_action(self, action):
        return getattr(self, "do_%s" % action, None)

    def check_perms(self, session, repository=None):
        user = session.query(db.User).get(self.terminal.avatar.username)
        if user.is_admin:
            return True
        if repository:
            return user in repository.managers
        return False

    def do_help(self, cmd=None, format=None, extended=True):
        """Get help for a all or a specific command."""
        log.debug("Received help request. CMD: %r", cmd)
        if cmd:
            func = self.get_action(cmd)
            if not func and cmd in self.commands:
                log.debug("Calling regular help for command %s" % cmd)
                for line in self.commands[cmd].do_help(format=format,
                                                       extended=extended):
                    yield line
                return
            if not func and cmd not in self.commands:
                raise CommandNotFound(cmd)
            elif func:
                log.debug("Found function %s for command %s", func, cmd)
                cmd_line = extended and ' '.join(self.get_doc(func)) or \
                    " %%(LG)s%s%%(RST)s: %s" % (cmd,
                                                ' '.join(self.get_doc(func)))
                if format and not extended:
                    cmd_line = format % (cmd, ' '.join(self.get_doc(func)))
                yield cmd_line
                yield self.nextLine
                if extended:
                    usage = self.get_usage(func, self.cmdname, cmd)
                    yield usage
                    yield self.nextLine
                return
        if self.actions:
            yield "%(LR)sCommands:"
            yield self.nextLine
            longest = max([len(command) for command in self.actions])
            format = '%%%%(LG)s%%+%ds%%%%(RST)s: %%s'
            for command in sorted(self.actions):
                for line in self.do_help(command, format % (longest+1),
                                         extended=False):
                    yield line

        commands = filter(None, self.commands.keys())
        if commands:
            log.debug("SubCommands: %r", commands)
            yield "%(LR)sSub-Commands:"
            yield self.nextLine
            longest = max([len(command) for command in commands])
            for command in commands:
                yield format % (longest+2) % (
                    command, ' '.join(self.get_doc(self.commands[command]))
                )
                yield self.nextLine

    def nextLine(self):
        self.terminal.nextLine()
