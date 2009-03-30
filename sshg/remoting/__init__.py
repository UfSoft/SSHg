# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.remoting
    ~~~~~~~~~~~~~

    This module holds the remote configuration services that SSHg provides.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.internet.threads import defer, deferToThread
from twisted.web.resource import Resource
from pyamf.remoting.gateway import expose_request
from pyamf.flex import ArrayCollection
from sshg.database import require_session
from sshg import logger

__all__ = ['logger', 'defer', 'deferToThread', 'expose_request', 'Resource',
           'require_session', 'ArrayCollection']


from sshg.remoting import auth, locales, users

services = {
    'SSHg.auth'     : auth.Authentication(),
    'SSHg.locales'  : locales.LocalesResource(),
    'SSHg.users'    : users.UsersResource()
}
