# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.routing import Map, Rule, Submount
from sshg.web.utils import require_admin, require_manager
from sshg.web.views import account, accounts, admin, repos

url_map = Map([
    Rule('/', endpoint='admin'),
    Rule('/shared/<file>', endpoint='shared', build_only=True),
    Submount('/account', [
        Rule('/', endpoint="account.prefs"),
        Rule('/login', endpoint="account.login"),
        Rule('/logout', endpoint="account.logout"),
        Rule('/reset', endpoint="account.reset"),
        Rule('/confirm/', endpoint="account.confirm",
             defaults={'confirm_hash': None}),
        Rule('/confirm/<confirm_hash>', endpoint="account.confirm"),
    ]),
    Submount('/accounts', [
        Rule('/', endpoint='accounts.index'),
        Rule('/new', endpoint='accounts.new'),
        Rule('/edit/<username>', endpoint='accounts.edit'),
    ]),
    Submount('/repos', [
        Rule('/', endpoint='repos.index'),
        Rule('/new', endpoint='repos.new'),
        Rule('/edit/<reponame>', endpoint='repos.edit'),
    ]),
])

handlers = {
    'admin': admin.index,

    # Authentication/Prefs Views
    'account.login':    account.login,
    'account.logout':   account.logout,
    'account.prefs':    account.preferences,
    'account.reset':    account.reset,
    'account.confirm':  account.confirm,

    # Accounts administration
    'accounts.index':   require_manager(accounts.index),
    'accounts.new':     require_manager(accounts.new),
    'accounts.edit':    require_manager(accounts.edit),

    # Repositories Administration
    'repos.index':      require_manager(repos.index),
    'repos.new':        require_admin(repos.new),
    'repos.edit':       require_manager(repos.edit),
}
