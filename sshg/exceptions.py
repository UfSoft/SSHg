# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

class InvalidRepository(Exception):
    message = "The path does not point to a valid mercurial repository."

class InvalidRepositoryPath(Exception):
    message = "The path to the repository does not exist."
