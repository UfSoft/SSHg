# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from babel.messages.mofile import read_mo
from sshg import config
from sshg.remoting import *

log = logging.getLogger(__name__)

class LocalesResource(Resource):

    @expose_request
    def get_translations(self, request, sent_locale):
        def _get_translations():
            translations = []
            locale = config.locales.get(sent_locale)
            catalog = read_mo(open(locale.get('path'), 'rb'))
            for msg in list(catalog)[1:]:
                translations.append(
                    {'msgid': msg.id,
                     'msgstr': msg.string and msg.string or msg.id})
                request.session.locale = locale
            return translations

        return defer.maybeDeferred(_get_translations)

    @expose_request
    def get_locales(self, request):
        def _get_locales():
            locales = ArrayCollection()
            for locale, details in config.locales.iteritems():
                locales.addItem({'locale': locale,
                                 'label': details.get('name')})
            return locales
        return defer.maybeDeferred(_get_locales)
