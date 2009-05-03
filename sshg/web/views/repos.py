# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from sshg.web.views import *

log = logger.getLogger(__name__)

def index(request):
    if request.method != 'POST':
        repos = request.user.manages.all()
        return generate_template('repos/index.html', repos=repos)
