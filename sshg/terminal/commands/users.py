# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from sshg.terminal.commands import *

log = logger.getLogger(__name__)

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
        """Add a public for a user. Please consider SFTP to manage keys"""
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
