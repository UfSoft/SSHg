# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.portals
    ~~~~~~~~~~~~

    This module is responsible the needed authentication Portals.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from twisted.cred.portal import Portal

class MercurialRepositoriesPortal(Portal):
    """Mercurial Repositories Portal"""
