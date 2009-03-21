# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================
"""
Mercurial Repositories SSH Server
=================================

"""

__import__('pkg_resources').declare_namespace(__name__)

__version__     = '0.1'
__package__     = 'SSHg'
__summary__     = "Mercurial repositories SSH server"
__author__      = 'Pedro Algarvio'
__email__       = 'ufs@ufsoft.org'
__license__     = 'BSD'
__url__         = 'https://hg.ufsoft.org/SSHg'
__description__ = __doc__

import sys
from types import ModuleType

sys.modules['sshg.config'] = config = ModuleType('config')
sys.modules['sshg.application'] = application = ModuleType('application')
