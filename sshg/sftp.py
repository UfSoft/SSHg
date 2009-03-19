# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.sftp
    ~~~~~~~~~

    This module implements the SFTP protocol.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import struct
from os import rename
from os.path import join, basename
from twisted.conch import unix
from twisted.conch.ssh import filetransfer
from twisted.python import log
from twisted.internet import defer

from twisted.conch.unix import UnixSFTPFile, UnixSFTPDirectory

# SSH_FX_NO_SPACE_ON_FILESYSTEM = 14
# SSH_FX_QUOTA_EXCEEDED = 15

class LimittedUnixSFTPFile(UnixSFTPFile):
    file_size = 0
    file_limit = 51200 # Approximately 130 lines of pub keys; more than enough

    def writeChunk(self, offset, data):
        if self.file_size > self.file_limit:
            raise filetransfer.SFTPError(
                filetransfer.FX_PERMISSION_DENIED,
                "File size limit of %i bytes reached" % self.file_limit)
        uploaded = UnixSFTPFile.writeChunk(self, offset, data)
        self.file_size += uploaded
        return uploaded

class SFTPFileTransfer(unix.SFTPServerForUnixConchUser):
    """Custom SFTP file transfer.
    Provides fixed size upload limit and disallows some unsafe and unneeded
    operations for what sshg is intended for.
    """

    def __init__(self, avatar):
        unix.SFTPServerForUnixConchUser.__init__(self, avatar)

    def gotVersion(self, version, extData):
        return {}

    def openFile(self, filename, flags, attrs):
        """Overridden method to provide our own limited size uploads."""
        return LimittedUnixSFTPFile(self, self._absPath(filename), flags, attrs)

    def openDirectory(self, path):
        """Overridden method to disallow writing or opening files outside
        the created temporary directory.
        """
        # Ignore any path passed, everything will be done on users home dir
        path = self.avatar.getHomeDir()
        return UnixSFTPDirectory(self, path)

    def realPath(self, path):
        path = '/' # Fake the path
        return path

    def _notimpl(self, *args, **kwargs):
        raise filetransfer.SFTPError(filetransfer.FX_PERMISSION_DENIED,
                                     "Operation Not Supported")

    def renameFile(self, oldpath, newpath):
        """Overridden method to disallow writing or opening files outside
        the created temporary directory.
        """
        # We support renaming because some clients first upload a *.part
        # file and then rename it
        oldpath = join(self.avatar.getHomeDir(), basename(oldpath))
        newpath = join(self.avatar.getHomeDir(), basename(newpath))
        log.msg("Trying to rename file: %r -> %r" % (oldpath, newpath))
        try:
            rename(oldpath, newpath)
        except:
            log.err()
            raise filetransfer.SFTPError(filetransfer.FX_PERMISSION_DENIED,
                                         "Operation Failed")

    makeDirectory = removeDirectory = readLink = makeLink = _notimpl
    removeFile = extendedRequest = _notimpl


class FileTransferServer(filetransfer.FileTransferServer):
    """Custom SFTP file transfer server.
    Provides fixed size upload limit and disallows some unsafe and unneeded
    operation for what sshg is intended for.
    """

    def packet_OPEN(self, data):
        """Overridden method to disallow writing or opening files outside
        the created temporary directory.
        """
        requestId = data[:4]
        data = data[4:]
        filename, data = filetransfer.getNS(data)
        flags ,= struct.unpack('!L', data[:4])
        data = data[4:]
        attrs, data = self._parseAttributes(data)
        # Force file to be written on the same dir. No change dir's allowed
        filename = basename(filename)

        assert data == '', 'still have data in OPEN: %s' % repr(data)
        d = defer.maybeDeferred(self.client.openFile, filename, flags, attrs)
        d.addCallback(self._cbOpenFile, requestId)
        d.addErrback(self._ebStatus, requestId, "open failed")

    def packet_OPENDIR(self, data):
        """Overridden method to disallow writing or opening files outside
        the created temporary directory.
        """
        requestId = data[:4]
        data = data[4:]
        path, data = filetransfer.getNS(data)
        # No change dir's allowed
        path = basename(path)
        assert data == '', 'still have data in OPENDIR: %s' % repr(data)
        d = defer.maybeDeferred(self.client.openDirectory, path)
        d.addCallback(self._cbOpenDirectory, requestId)
        d.addErrback(self._ebStatus, requestId, "opendir failed")

    def packet_STAT(self, data, followLinks = 1):
        """Overridden method to disallow writing or opening files outside
        the created temporary directory.
        """
        followLinks = 0 # Don't follow links
        requestId = data[:4]
        data = data[4:]
        path, data = filetransfer.getNS(data)
        # No change dir's allowed
        if path not in ('/', '/authorized_keys', '/authorized_keys.part'):
            log.msg("Original path: %s" % path)
            path = basename(path)
            log.msg("New path: %s" % path)
        assert data == '', 'still have data in STAT/LSTAT: %s' % repr(data)
        d = defer.maybeDeferred(self.client.getAttrs, path, followLinks)
        d.addCallback(self._cbStat, requestId)
        d.addErrback(self._ebStatus, requestId, 'stat/lstat failed')

    def packet_SETSTAT(self, data):
        """Overridden method to disallow writing or opening files outside
        the created temporary directory.
        """
        requestId = data[:4]
        data = data[4:]
        path, data = filetransfer.getNS(data)
        attrs, data = self._parseAttributes(data)
        # No change dir's allowed
        path = basename(path)
        if data != '':
            log.msg('WARN: still have data in SETSTAT: %s' % repr(data))
        d = defer.maybeDeferred(self.client.setAttrs, path, attrs)
        d.addCallback(self._cbStatus, requestId, 'setstat succeeded')
        d.addErrback(self._ebStatus, requestId, 'setstat failed')


