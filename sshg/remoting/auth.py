# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.remoting.auth
    ~~~~~~~~~~~~~~~~~~

    This module holds the remote authentication required to configure SSHg
    remotely.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from sshg.remoting import *
from sshg.database import User

log = logger.getLogger(__name__)

class AuthenticationNeeded(Exception):
    """Exception which triggers the required authentication code on the
    flex side."""

class Authentication(Resource):

    @expose_request
    def login(self, request, user_details):
        def failure(exception):
            log.error(exception)
            raise AuthenticationNeeded
        return defer.maybeDeferred(self._login, request,
                                   user_details).addErrback(failure)

    @require_session
    def _login(self, request, user_details, session=None):
        if getattr(request.session, 'authenticated', False):
            return 'Logged In.'
        user = session.query(User).get(user_details.get('username'))
        log.debug("User authenticating %s", user)

        if not user:
            log.debug("No user: %s", user)
            raise AuthenticationNeeded
        if not user.authenticate(user_details.get('password')):
            log.debug(user_details)
            raise AuthenticationNeeded
        request.session.user = user
        request.session.authenticated = True
        log.debug('login OK for user "%s"', user.username)
        return 'Logged In.'

    @expose_request
    def logout(self, request):
        def _logout():
            request.session.expire()
            return 'Logged Out'
        return defer.maybeDeferred(_logout)


