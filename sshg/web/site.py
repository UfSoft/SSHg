# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import sshg
from os.path import join, dirname

from OpenSSL import SSL
from twisted.web import static
from nevow import entities, loaders, rend, tags
from sshg import application, config

application.templates = join(dirname(sshg.__file__), 'templates')
application.static = join(dirname(sshg.__file__), 'static')

class SSHgWebConfigRoot(rend.Page):
    addSlash = True
    docFactory = loaders.xmlfile(join(application.templates, 'site.html'))

    child_css = static.File(join(application.static, 'css'))
    child_images = static.File(join(application.static, 'imgs'))

    def render_navigation(self, context, data):
        context.tag.clear()
        context.tag.children.append(tags.li['foo'])
        return context.tag

    def renderHTTP(self, ctx):
        print entities.copy, entities.mdash
#        ctx['entities'] = entities
        print ctx
        return rend.Page.renderHTTP(self, ctx)

    def render_HEAD(self, ctx, data):
        pass

    def getContext(self):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file(config.certificate)
        ctx.use_privatekey_file(config.private_key)
        return ctx


