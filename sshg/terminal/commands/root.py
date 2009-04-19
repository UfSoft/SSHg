# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from sshg.terminal.commands import *
from sshg.terminal.commands.repositories import RepositoriesCommands
from sshg.terminal.commands.users import UserCommands


class RootAdminCommands(BaseCommand):
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

    def do_add_pubkey(self, public_key):
        """Add a public to your user. Please consider SFTP to manage keys"""
        username = self.terminal.avatar.username
        session = db.session()
        user = session.query(db.User).get(username)
        if not user:
            yield "User '%s' is not known" % username
            return
        user.keys.append(db.PublicKey(''.join(public_key)))
        session.commit()
        yield "Public key added."

    def do_whoami(self):
        """Tell's you who you are."""
        yield "You're %s!" % self.terminal.avatar.username
