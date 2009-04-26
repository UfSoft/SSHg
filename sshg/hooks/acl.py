# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import os, pprint, simplejson
from os import environ
from mercurial import util
from mercurial.i18n import _


def buildmatch(ui, repo, username, pats):
    '''return tuple of (match function, list enabled).'''
    if pats:
        return util.matcher(repo.root, names=pats)[1]
    return util.never


def hook(ui, repo, hooktype, node=None, source=None, **kwargs):
    if hooktype != 'pretxnchangegroup':
        raise util.Abort(_('config error - hook type "%s" cannot stop '
                           'incoming changesets') % hooktype)

    print '\n\n\n', repo
    print environ.get('SSHg.USERNAME', None)
    print simplejson.loads(environ.get('SSHg.ALLOW', None))
    print simplejson.loads(environ.get('SSHg.DENY', None))
    print source

    # Who's pushing
    allow_rules = environ.get('SSHg.ALLOW', None)
    deny_rules = environ.get('SSHg.DENY', None)
    username = environ.get('SSHg.USERNAME', None)
    source_rules = environ.get('SSHg.SOURCE', None)
    if not allow_rules or not deny_rules or not source_rules or not username:
        raise util.Abort("Something's wrong with your setup. At least one of "
                         "the necessary environment keys is not present.")

    # How should I handle source too?
    if source not in simplejson.loads(source_rules):
        ui.debug(_('acl: changes have source "%s" - skipping\n') % source)
        return


    # Get Allow/Deny Rules
    allow = buildmatch(ui, repo, username, simplejson.loads(allow_rules))
    deny = buildmatch(ui, repo, username, simplejson.loads(deny_rules))

    raise util.Abort("I just need to stop this")
    # Check Them!
    for rev in xrange(repo[node], len(repo)):
        ctx = repo[rev]
        for f in ctx.files():
            if deny and deny(f):
                ui.debug(_('acl: user %s denied on %s\n') % (username, f))
                raise util.Abort(_('acl: access denied for changeset %s') % ctx)
            if allow and not allow(f):
                ui.debug(_('acl: user %s not allowed on %s\n') % (username, f))
                raise util.Abort(_('acl: access denied for changeset %s') % ctx)
        ui.debug(_('acl: allowing changeset %s\n') % ctx)
