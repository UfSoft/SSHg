# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from os import path
from decorator import decorator
from genshi import Stream
from genshi.builder import tag
from genshi.filters.html import HTMLFormFiller
from genshi.template import TemplateLoader, MarkupTemplate, NewTextTemplate
from werkzeug.wrappers import BaseRequest, BaseResponse, ETagRequestMixin
from werkzeug.local import Local, LocalManager
from werkzeug.contrib.securecookie import SecureCookie
from werkzeug.exceptions import NotFound, Unauthorized, Forbidden
from sshg import config, database as db, logger


__all__ = ['local', 'local_manager', 'request', 'application',
           'generate_template', 'url_for', 'shared_url', 'format_datetime',
           'Request', 'Response']

# calculate the path to the templates an create the template loader
TEMPLATE_PATH = path.join(path.dirname(__file__), 'templates')
template_loader = TemplateLoader(TEMPLATE_PATH, auto_reload=True,
                                 variable_lookup='lenient')

# context locals.  these two objects are use by the application to
# bind objects to the current context.  A context is defined as the
# current thread and the current greenlet if there is greenlet support.

local = Local()
local_manager = LocalManager([local])
request = local('request')
application = local('application')

log = logger.getLogger(__name__)

def generate_template(template_name, **context):
    """Load and generate a template."""
    formfill = context.pop('formfill', None)
    context.update(
        url_for=url_for,
        shared_url=shared_url,
        format_datetime=format_datetime,
        pretty_size=pretty_size,
        request=request
    )
    if template_name.endswith('.txt'):
        cls = NewTextTemplate
    else:
        cls = MarkupTemplate
    stream = template_loader.load(template_name, cls=cls).generate(**context)
    if formfill:
        return stream | HTMLFormFiller(data=formfill)
    return stream

def url_for(endpoint, *args, **kwargs):
    if hasattr(endpoint, '__url__'):
        return endpoint.__url__(*args, **kwargs)
    if 'force_external' in kwargs:
        force_external = kwargs.pop('force_external')
    else:
        force_external = False
    return application.url_adapter.build(endpoint, kwargs,
                                         force_external=force_external)

def shared_url(filename):
    """Returns a URL to a shared resource."""
    return url_for('shared', file=filename)

def format_datetime(obj):
    """Format a datetime object."""
    format = '%Y-%m-%d %H:%M:%S'
    if request.user:
        format = request.user.session.datetime_format.encode('utf-8')
    return obj.strftime(format)

def pretty_size(size, format='%.2f'):
    if not size:
        return '0 bytes'
    jump = 512
    if size < jump:
        return '%d bytes' % size
    units = ['KB', 'MB', 'GB', 'TB']
    i = 0
    while size >= jump and i < len(units):
        i += 1
        size /= 1024.
    return (format + ' %s') % (size, units[i - 1])

def flash(message, error=False, msg=False):
    key = 'infos'
    if error and msg:
        raise Exception("A flash msg cannot be error and msg at the same time")
    elif error:
        key = 'errors'
    elif msg:
        key = 'msgs'
    request.session.setdefault(key, []).append(message)


@decorator
def require_manager(fn, request, *args, **kwargs):
    log.debug(request.user)
    if request.user.is_manager:
        if request.endpoint == 'repos.edit':
            if not request.user.manages.filter_by(name=args[0]).first():
                raise Forbidden()
        elif request.endpoint == 'accounts.edit':
            from sshg.web import session
            account = session().query(db.User).get(args[0])
            if account and not account.can_be_managed_by(request.user):
                raise Forbidden("You do not have the required permission to "
                                "manage this account.")
        return fn(request, *args, **kwargs)
    raise Forbidden()

@decorator
def require_admin(fn, request, *args, **kwargs):
    log.debug(request.user)
    if request.user.is_admin:
        return fn(request, *args, **kwargs)
    raise Forbidden()


class Request(BaseRequest, ETagRequestMixin):
    user = None
    """Simple request subclass that allows to bind the object to the
    current context.
    """
    def bind_to_context(self):
        local.request = self

    def login(self, user, permanent=False):
        self.user = user
        self.session['uuid'] = user.uuid
        self.session['lv'] = user.session.last_visit
        if permanent:
            self.session['pmt'] = permanent

    def logout(self):
        self.session.clear()

    def setup_cookie(self):
        self.session = SecureCookie.load_cookie(
            self, config.web.cookie_name, config.web.secret_key.encode('utf-8')
        )

    def load_persistent_sessions(self):
        from sshg.web import session
        uuid = self.session.get('uuid', None)
        user = session.query(db.User).filter_by(uuid=uuid).first()

        if not uuid or not user:
            raise Unauthorized()

        self.login(user)
        self.user.session.update_last_visit()
        if not self.user.email and self.user.changes.count() < 1:
            flash(tag("Please take the time to ",
                      tag.a("update", href=url_for('account.prefs')),
                      " your email address."))
        session.commit()

class Response(BaseResponse):
    """
    Encapsulates a WSGI response.  Unlike the default response object werkzeug
    provides, this accepts a genshi stream and will automatically render it
    to html.  This makes it possible to switch to xhtml or html5 easily.
    """

    default_mimetype = 'text/html'

    def __init__(self, response=None, status=200, headers=None, mimetype=None,
                 content_type=None):
        if isinstance(response, Stream):
            response = response.render('html', encoding=None, doctype='html')
        BaseResponse.__init__(self, response, status, headers, mimetype,
                              content_type)
