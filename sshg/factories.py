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
from os.path import dirname, join, isdir, isfile
from twisted.conch.ssh import factory, keys
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor

from babel.core import Locale
from babel.support import Translations

from pyamf.remoting.gateway import expose_request
from pyamf.remoting.gateway.twisted import TwistedGateway

from OpenSSL import SSL

from pyamf import amf3, register_class

from sshg import config, logger
from sshg.database import Repository, User, PublicKey
from sshg.remoting import services
from sshg.remoting.auth import AuthenticationNeeded

log = logger.getLogger(__name__)

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
        self.setup_pyamf()
        self.setup_translations()

    def setup_pyamf(self):
        # Setup PyAMF
        # Set this to true so that returned objects and arrays are bindable
        amf3.use_proxies_default = True

        SSH_AMF_MODEL_NAMESPACE = "org.ufsoft.sshg.models"

        register_class(Repository, '%s.Repository' % SSH_AMF_MODEL_NAMESPACE,
                       attrs=['name', 'path', 'size', 'quota'])
        register_class(User, '%s.User' % SSH_AMF_MODEL_NAMESPACE,
                       attrs=['username', 'password', 'added',
                              'last_login', 'is_admin', 'locked_out'])
        register_class(PublicKey, '%s.PublicKey' % SSH_AMF_MODEL_NAMESPACE,
                       attrs=['key', 'added', 'used_on'])


    def setup_translations(self):
        config.locales = {}
        locales_path = join(dirname(__file__), 'locale')
        for locale in listdir(locales_path):
            locale_file = join(locales_path, locale, 'LC_MESSAGES',
                               'messages.mo')
            if isfile(locale_file):
                config.locales[locale] = {
                    'path': locale_file,
                    'name': Locale.parse(locale).display_name
                }

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
        print 123, config.static_dir
        if isdir(config.static_dir):
            for filename in listdir(config.static_dir):
                filepath = join(config.static_dir, filename)
                if filename == 'index.html':
                    # Serve index.html from /
                    filename = ''
                root.putChild(filename, File(filepath))

        gateway = TwistedGateway(services, expose_request=False,
                                 preprocessor=self.preprocessor)
        gateway.logger = logger.getLogger('sshg.pyamf')
        root.putChild('services', gateway)
        return root

    @expose_request
    def preprocessor(self, request, service_request, *args, **kwargs):
        log.debug('\n\n\n Preprocess %s %s' % (args, kwargs))
        try:
            if not request.session:
                request.getSession()
            request.factory = self

            user = getattr(request.session, 'user', None)
            locale = user and getattr(user, 'locale', 'en_US') or 'en_US'
            if getattr(request.session, 'locale', None) != locale:
                request.session.locale = locale
                request.session.translations = Translations(
                    open(config.locales.get(locale).get('path'), 'rb')
                )
                request.session.touch()
            del user, locale

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
