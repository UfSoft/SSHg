# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.avatars
    ~~~~~~~~~~~~

    This module is responsible the needed authentication Avatars.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import binascii
import shutil
import tempfile
from os.path import abspath, join
from twisted.conch.insults import insults
from twisted.conch.ssh import keys
from twisted.conch.ssh.session import ISession
from twisted.conch.ssh.filetransfer import SFTPError, ISFTPServer
from twisted.conch.unix import UnixConchUser
from twisted.internet import defer
from twisted.python import components, log

from sshg import logger
from sshg.sessions import (MercurialSession, MercurialAdminSession,
                           FixedSSHSession)
from sshg.sftp import SFTPFileTransfer, FileTransferServer
from sshg.database import require_session, User, PublicKey

# XXX: Implement username/password authentication too ???

log = logger.getLogger(__name__)

def validPublicKey(public_key_contents):
    try:
        keys.Key.fromString(data=public_key_contents)
    except (binascii.Error, keys.BadKeyError):
        return False
    return True

class MercurialUser(UnixConchUser, components.Adapter):
    homeDir = _user = _keys = keys_file_path = None

    def __init__(self, original, username):
        components.Adapter.__init__(self, original)
        UnixConchUser.__init__(self, username)
        self.username = username
        self.channelLookup.update({'session': FixedSSHSession})
        self.subsystemLookup.update({'sftp': FileTransferServer})

    def _runAsUser(self, f, *args, **kw):
        # Override UnixConchUser._runAsUser because we're not changing
        # uid's nor gid's.
        # Home directories are created, destroyed and populated at runtime
        # because they will only hold the public keys file
        try:
            f = iter(f)
        except TypeError:
            f = [(f, args, kw)]
        for i in f:
            func = i[0]
            args = len(i)>1 and i[1] or ()
            kw = len(i)>2 and i[2] or {}
            try:
                r = func(*args, **kw)
            except SFTPError:
                # Maybe uploading a file bigger than it should be?
                break
        return r

    @property
    @require_session
    def user(self, session=None):
        return session.query(User).get(self.username)

    @property
    @require_session
    def keys(self, session=None):
        return [k.key.strip() for k in
                session.query(User).get(self.username).keys]

    def getHomeDir(self):
        if not self.homeDir:
            self.homeDir = tempfile.mkdtemp()
            log.debug('Creating home directory for user "%s": %s' % (
                      self.username, self.homeDir))

            # Populate keys file with current user's keys
            self.keys_file_path = abspath(join(self.homeDir, "authorized_keys"))
            keys_file = open(self.keys_file_path, 'w')
            for key in self.keys:
                keys_file.write(key + '\n')
            keys_file.close()
        return self.homeDir

    def logout(self):
        return defer.maybeDeferred(self._logout)

    @require_session
    def _logout(self, session=None):
        log.debug('User "%s" logging out' % self.username)
        user = session.query(User).get(self.username)
        pkeys = [k.key.strip() for k in user.keys]

        if self.homeDir:
            log.debug("Checking if user updated the public keys file")
            # Perhaps check each file in the user home dir???
            file_keys = []
            lineno = 1
            for line in open(self.keys_file_path):
                key = line.strip()
                if not validPublicKey(key):
                    log.debug("Ignoring line %i. Invalid key" % lineno )
                elif key == user.last_used_key.key:
                    log.debug("Key on line %i was used to login. "
                            "Skipping." % lineno)
                    if key in pkeys:
                        pkeys.pop(pkeys.index(key))
                else:
                    file_keys.append(key)
                lineno += 1
            deleted_keys = 0
            added_keys = 0
            for key in file_keys:
                if key in pkeys:
                    pkeys.pop(pkeys.index(key))
                elif key not in pkeys:
                    # Add new keys to database
                    added_keys += 1
                    user.keys.append(PublicKey(key))
            for dbkey in user.keys:
                # Any existing keys in self.keys were deleted from file and
                # thus should be deleted from database
                if dbkey.key in pkeys:
                    # Sanity Check
                    if dbkey.key != user.last_used_key.key:
                        deleted_keys += 1
                        session.delete(dbkey)

            session.commit()
            log.debug("User %s added %s and removed %s keys." % (
                    self.username, added_keys, deleted_keys))
            # Now remove any evidences from the file system
            log.debug("Removing temporary home dir of user %s" % self.username)
            shutil.rmtree(self.homeDir, True)
        # Remove last used key from user
        user.last_used_key = None
        log.debug('User "%s" logged out' % self.username)


class MercurialAdmin(MercurialUser):

    def openShell(self, protocol):
        log.debug("SHELL")
        serverProtocol = insults.ServerProtocol(insults.TerminalProtocol)

        pass



components.registerAdapter(MercurialSession, MercurialUser, ISession)
components.registerAdapter(MercurialAdminSession, MercurialAdmin, ISession)
components.registerAdapter(SFTPFileTransfer, MercurialUser, ISFTPServer)
