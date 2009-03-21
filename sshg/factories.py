# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.factories
    ~~~~~~~~~~~~~~

    This module is responsible the service factories.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

import logging

from os import listdir
from os.path import dirname, join, isdir
from twisted.conch.ssh import factory, keys
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.static import File

from pyamf.remoting.gateway import expose_request
from pyamf.remoting.gateway.twisted import TwistedGateway

from OpenSSL import SSL

from sshg import config
from sshg.remoting import services
from sshg.remoting.auth import AuthenticationNeeded

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s'
)

log = logging.getLogger(__name__)

class MercurialReposFactory(factory.SSHFactory):

    def __init__(self, realm, portal):
        realm.factory = portal.factory = self
        self.realm = realm
        self.portal = portal

        self._privateKey = keys.Key.fromString(open(config.private_key).read())
        self._publicKey = self._privateKey.public()

    def getPublicKeys(self):
        return {'ssh-rsa': self._publicKey}

    def getPrivateKeys(self):
        return {'ssh-rsa': self._privateKey}


class ConfigurationFactory(Site):
    def __init__(self, logPath=None, timeout=60*60*12):
        resource = self.build_resources()
        Site.__init__(self, resource, logPath, timeout)

    def build_resources(self):
        root = Resource()
        # Add the config/static files we're supplying
        static_files_dir = join(dirname(__file__), 'static')
        for filename in listdir(static_files_dir):
            filepath = join(static_files_dir, filename)
            if filename == 'index.html':
                filename = ''
            root.putChild(filename, File(filepath))

        # Override with the files the user provide from it's dir
#        if isdir(config.static_files):
#            static_files_dir = config.static_files
#            for filename in listdir(static_files_dir):
#                filepath = join(static_files_dir, filename)
#                if filename == 'index.html':
#                    # Serve index.html from /
#                    filename = ''
#                root.putChild(filename, File(filepath))

        gateway = TwistedGateway(services, expose_request=False,
                                 preprocessor=self.preprocessor)
        gateway.logger = logging.getLogger('sshg.pyamf')
        root.putChild('services', gateway)
        return root

    @expose_request
    def preprocessor(self, request, service_request, *args, **kwargs):
        print '\n\n\n Preprocess', args, kwargs
        try:
            if not request.session:
                request.getSession()
            request.factory = self

#            user = getattr(request.session, 'user', None)
#            locale = user and user.locale or 'en_US'
#            if getattr(request.session, 'locale', None) != locale:
#                request.session.locale = locale
#                request.session.translations = Translations(
#                    open(request.factory.config.locales.get(locale).get('path'),
#                         'rb')
#                )
#                request.session.touch()
#            del user, locale

            if service_request.method in ('login', 'get_translations',
                                          'get_locales'):
                return
            try:
                return request.session.authenticated
            except AttributeError:
                raise AuthenticationNeeded
        except Exception, err:
            print 123456
            raise err

    def getContext(self):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file(config.certificate)
        ctx.use_privatekey_file(config.private_key)
        return ctx
