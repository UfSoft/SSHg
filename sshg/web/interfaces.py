# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from zope.interface import Interface

class IURLHandler(Interface):

    def getUrlHref(cls):
        pass

    def getUrlName(cls):
        pass

print 88800000, dir(IURLHandler)
