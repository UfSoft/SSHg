# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import os.path
from sshg.terminal.commands import *

log = logger.getLogger(__name__)

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
        return "Size: %s" % (repo.size==0 and 'unlimited' or repo.size)

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
