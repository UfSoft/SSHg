# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import os.path
from inspect import getargspec
from sshg import database as db, logger

log = logger.getLogger(__name__)

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



class UserCommands(BaseCommand):
    """User Commands"""

    cmdname = 'users'

    def do_list(self):
        """List Available Users."""
        yield "%(HI)s Available Users:"
        yield self.nextLine
        session = db.session()
        for username in session.query(db.User.username).all():
            log.debug("Found username: %s", username[0])
            yield u'  ' + username[0]
            yield self.nextLine

    def do_add(self, username, password, is_admin=False):
        """Add a new user."""
        session = db.session()
        if not self.check_perms(session):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
        user = db.User(username, password, bool(is_admin))
        session.add(user)
        session.commit()
        yield "User %s added" % username

    def do_add_pubkey(self, username, public_key):
        """Add a public key for a user."""
        session = db.session()
        if not self.check_perms(session):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
        user = session.query(db.User).get(username)
        if not user:
            yield "User '%s' is not known" % username
            return
        user.keys.append(db.PublicKey(''.join(public_key)))
        session.commit()
        yield "Public key added."

    def do_details(self, username):
        """Show user details."""
        session = db.session()
        if not self.check_perms(session):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
        user = session.query(db.User).get(username)
        if not user:
            yield "User '%s' is not known" % username
            return
        yield "%%(HI)s   Username%%(RST)s: %s" % user.username
        yield self.nextLine
        yield "%%(HI)s   Added On%%(RST)s: %s" % user.added_on
        yield self.nextLine
        yield "%%(HI)s Last Login%%(RST)s: %s" % user.last_login
        yield self.nextLine
        yield "%%(HI)s Locked Out%%(RST)s: %s" % user.locked_out
        yield self.nextLine
        yield "%%(HI)s   Is Admin%%(RST)s: %s" % user.is_admin
#        yield self.nextLine

    def do_delete(self, username):
        """Remove a user from database"""
        session = db.session()
        if not self.check_perms(session):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
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
        if not self.check_perms(session):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
        user = session.query(db.User).get(username)
        if not user:
            yield "User '%s' is not known" % username
            return
        user.change_password(password)
        session.commit()
        yield "Password changed for user %s" % username



class BaseRepositoryCommands(BaseCommand):

    def _exists(self, session, reponame):
        return session.query(db.Repository).get(reponame)

class RepositoryUsersCommands(BaseRepositoryCommands):
    """Repository users commands."""

    cmdname = 'users'

    def do_list(self, reponame):
        """List repository users."""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            yield  "A repository by the name of %s was not found." % reponame
            return
        if not self.check_perms(session, repo):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
        log.debug(repo)
        yield "%(HI)s Repository Users:"
        yield self.nextLine
        if not repo.users:
            yield "Repository has no users."
            return
        for user in repo.users:
            yield "  %s" % user.username
            yield self.nextLine

class RepositoryManagersCommands(BaseRepositoryCommands):
    """Repository managers commands."""

    cmdname = 'managers'

    def do_list(self, reponame):
        """List repository users."""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            yield  "A repository by the name of %s was not found." % reponame
            return
        if not self.check_perms(session, repo):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
        log.debug(repo)
        yield "%(HI)s Repository Managers:"
        yield self.nextLine
        if not repo.managers:
            yield "  Repository has no managers."
            return
        for user in repo.managers:
            yield "  %s" % user.username
            yield self.nextLine

    def do_add(self, reponame, username):
        """Add username as a manager of the repository."""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            yield  "A repository by the name of %s was not found." % reponame
            return
        if not self.check_perms(session, repo):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
        log.debug(repo)

        user = session.query(db.User).get(username)
        if not user:
            yield "User %s is not known" % username
            return
        repo.managers.append(user)
        session.commit()
        yield "User %s added to the %s repository managers" % (username,
                                                               reponame)

    def do_delete(self, reponame, username):
        """Add username as a manager of the repository."""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            yield  "A repository by the name of %s was not found." % reponame
            return
        if not self.check_perms(session, repo):
            yield "%(LR)Error:%(RST)s You don't have the required permissions."
            return
        log.debug(repo)

        user = session.query(db.User).get(username)
        if not user:
            yield "User %s is not known" % username
            return
        repo.managers.pop(repo.managers.index(user))
        session.commit()
        yield "User %s deleted from the %s repository managers" % (username,
                                                                   reponame)


class RepositoriesCommands(BaseRepositoryCommands):
    """Repositories Commands"""

    cmdname = 'repos'
    __commands__ = [RepositoryUsersCommands, RepositoryManagersCommands]

    def do_list(self):
        """List available repositories"""
        session = db.session()
        repos = session.query(db.Repository.name).all()
        if not repos:
            yield "No available repositories"
            return
        yield "%(HI)s Available Repositories:"
        yield self.nextLine
        for repo in repos:
            yield "  %s" % repo[0]
            yield self.nextLine

    def do_add(self, reponame, repopath, size=0, quota=0):
        """Add repository."""
        session = db.session()
        if not self.check_perms(session):
            return "%(LR)Error:%(RST)s You don't have the required permissions."
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
        if not self.check_perms(session, repo):
            return "%(LR)Error:%(RST)s You don't have the required permissions."
        log.debug(repo)
        size = repo.get_size()
        return "Size: %s" % (size==0 and 'unlimited' or size)

    def do_quota(self, reponame, quota=0):
        """Check or set the repository's permitted quota"""
        session = db.session()
        repo = self._exists(session, reponame)
        if not repo:
            return "A repository by the name of %s was not found." % reponame
        if not self.check_perms(session, repo):
            return "%(LR)Error:%(RST)s You don't have the required permissions."
        log.debug(repo)
        if quota:
            repo.quota = int(quota)
            session.commit()
            return "Repository quota updated to %s" % (repo.quota==0 and
                                                       'unlimited' or
                                                       repo.quota)
        return "Quota: %s" % (repo.quota==0 and 'unlimited' or repo.quota)


class BasicAdminCommands(BaseCommand):
    """Administration Basic Commands"""
    cmdname = None

    __commands__ = [UserCommands, RepositoriesCommands]

    def do_exit(self):
        """Exit admin shell."""
        self.terminal.loseConnection()

    def do_password(self, password):
        """Change your password."""
        username = self.terminal.avatar.username
        session = db.session()
        user = session.query(db.User).get(username)
        if not user:
            yield "User '%s' is not known" % username
            return
        user.change_password(password)
        session.commit()
        yield "Password changed for user %s" % username

    def do_whoami(self):
        """Tell's you who you are."""
        yield "You're %s!" % self.terminal.avatar.username
