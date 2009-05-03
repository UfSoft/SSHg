# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from genshi.core import Stream
from os import path
from time import time

from sshg import application, config, logger, notification
from sshg.web import session
from sshg.web.urls import url_map, handlers
from sshg.web.utils import (Request, Response, local, local_manager,
                            generate_template, url_for)
from sqlalchemy.exceptions import InvalidRequestError
from werkzeug.exceptions import HTTPException, NotFound, Unauthorized, Forbidden
from werkzeug.utils import ClosingIterator, SharedDataMiddleware, redirect

from twisted.web import wsgi
#: path to shared data
SHARED_DATA = path.join(path.dirname(__file__), 'shared')


MESSAGE_404 = ("The requested URL was not found on the server. If you entered"
               " the URL manually please check your spelling and try again.")

log = logger.getLogger(__name__)

class WSGIApplication(object):
    def __init__(self):
        self.url_map = url_map

        # apply our middlewares.   we apply the middlewares *inside* the
        # application and not outside of it so that we never lose the
        # reference to the `Screener` object.
        self._dispatch = SharedDataMiddleware(self.dispatch_request, {
            '/shared': SHARED_DATA
        })

        # free the context locals at the end of the request
        self._dispatch = local_manager.make_middleware(self._dispatch)

    def bind_to_context(self):
        """
        Useful for the shell.  Binds the application to the current active
        context.  It's automatically called by the shell command.
        """
        local.application = self

    def dispatch_request(self, environ, start_response):
        """Dispatch an incoming request."""
        # set up all the stuff we want to have for this request.  That is
        # creating a request object, propagating the application to the
        # current context and instantiating the database session.
        self.bind_to_context()
        request = Request(environ)
        request.config = config
        request.notification = application.notification
        request.bind_to_context()
        request.setup_cookie()

        self.url_adapter = url_map.bind_to_environ(environ)

        try:
            endpoint, params = self.url_adapter.match()
            try:
                request.load_persistent_sessions()
            except Unauthorized:
                # Allow login's; raise on everything else
                if endpoint not in ('account.login', 'account.reset',
                                    'account.confirm'):
                    raise
            request.endpoint = endpoint
            action = handlers[endpoint]
            response = action(request, **params)
            if isinstance(response, Stream):
                response = Response(response)
        except KeyError, e:
            log.debug("KeyError: %r", e)
            e.description = MESSAGE_404
            e.status = 404
            e.name = "Not Found"
            response = Response(generate_template('4xx.html', exception=e))
            response.status_code = 404
        except NotFound, e:
            log.debug("NotFound: %r", e)
            if e.code == 404:
                e.description = MESSAGE_404
            response = Response(generate_template('4xx.html', exception=e))
            response.status_code = e.code
            # Error Codes:
            #    404:    Not Found
            #    409:    Resource Conflict
            #    410:    Resource Gone
        except Unauthorized:
            response = redirect(url_for('account.login'))
        except Forbidden, e:
            response = Response(generate_template('4xx.html', exception=e))
        except HTTPException, e:
            response = e.get_response(environ)

        if request.session.should_save:
            if request.session.get('pmt'):
                max_age = 60 * 60 * 24 * 31
                expires = time() + max_age
            else:
                max_age = expires = None
            request.session.save_cookie(response, config.web.cookie_name,
                                        max_age=max_age, expires=expires,
                                        session_expires=expires)
        try:
            return ClosingIterator(response(environ, start_response),
                                   [local_manager.cleanup, session.remove])
        except InvalidRequestError:
            session.rollback()


    def __call__(self, environ, start_response):
        """Just forward a WSGI call to the first internal middleware."""
        return self._dispatch(environ, start_response)
