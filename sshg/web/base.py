# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import operator
import sshg
from os.path import join, dirname

from OpenSSL import SSL
from twisted.web import static
from nevow import loaders, inevow, rend, tags, url
from sshg import application, config

application.templates = join(dirname(sshg.__file__), 'templates')
application.static = join(dirname(sshg.__file__), 'static')

class SSHgWebConfigBase(rend.Page):

    addSlash = True
    docFactory = loaders.xmlfile(join(application.templates, 'site.html'))
    contentTemplateFile = join(application.templates, 'index.html')

    child_css = static.File(join(application.static, 'css'))
    child_images = static.File(join(application.static, 'imgs'))

    children = {}

    hrefHdlr = None
    hrefName = None

    def render_navigation(self, context, data):
        print 123, url.here.child, url.here.sibling
        request = inevow.IRequest(context)
        nav = context.tag.clear()

        handlers = SSHgWebConfigBase.__subclasses__()[:]
        handlers.sort(key=operator.attrgetter('hrefName'), reverse=True)

        for idx, child in enumerate(handlers):
            instance = child()
            print 123, url.here.child(instance.hrefHdlr), url.here.sibling(instance.hrefHdlr)
            self.children[instance.hrefHdlr] = instance
            if idx == len(handlers)-1:
                klass = 'first'
            elif idx == 0:
                klass = 'last'

            if instance.hrefHdlr not in (
                        request.path, request.path.lstrip('/').split('/')[0]):
                nav.children.append(
                    tags.li(_class=klass)[
                        tags.a(href=url.here.child(instance.hrefHdlr))[
                            instance.hrefName
                        ]
                    ])
            else:
                if klass:
                    klass += ' active'
                else:
                    klass = 'active'
                nav.children.append(tags.li(_class=klass)[instance.hrefName])

        return nav

    def render_content(self, context, data):
        tag = context.tag.clear()
        tag[loaders.xmlfile(join(application.templates,
                                 self.contentTemplateFile))]
        return tag

#    def locateChild(self, ctx, segments):
#        print 9876, ctx, segments
#        return rend.Page.locateChild(self, ctx, segments)
#
#    def childFactory(self, context, segment):
#        print 11111, context, segment
#        rend.Page.childFactory(self, context, segment)


    def getContext(self):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file(config.certificate)
        ctx.use_privatekey_file(config.private_key)
        return ctx


