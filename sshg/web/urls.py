# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from werkzeug.routing import Map, Rule, Submount
from sshg.web import views

url_map = Map([
    Rule('/', endpoint='admin'),
    Rule('/shared/<file>', endpoint='shared', build_only=True),
    Submount('/account', [
        Rule('/login', endpoint="account.login"),
        Rule('/logout', endpoint="account.logout"),
        Rule('/reset', endpoint="account.reset"),
        Rule('/delete', endpoint="account.delete"),
        Rule('/register', endpoint="account.register"),
        Rule('/preferences', endpoint="account.prefs"),
        Rule('/preferences/anonymous', endpoint="account.anonpref"),
        Rule('/verify', endpoint="account.verify"),
        Rule('/confirm/', endpoint="account.confirm",
             defaults={'confirm_hash': None}),
        Rule('/confirm/<confirm_hash>', endpoint="account.confirm"),
    ]),
])

handlers = {
    'admin': views.admin.index,

    # Authentication/Prefs Views
    'account.login':    views.account.login,
    'account.logout':   views.account.logout,
    'account.prefs':    views.account.preferences,
    'account.reset':    views.account.reset,
    'account.confirm':  views.account.confirm,
}
