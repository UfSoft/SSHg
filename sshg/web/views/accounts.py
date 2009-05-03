# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from sshg.web.views import *
from sshg.utils.crypto import gen_salt

log = logger.getLogger(__name__)

@require_manager
def index(request):
    if request.method != 'POST':
        accounts = session.query(db.User).all()
        return generate_template('accounts/index.html', accounts=accounts)

    selection = request.values.getlist('sel')
    log.debug("Selection: %r", selection)
    if 'delete' in request.values:
        for username in selection:
            log.debug("Deleting user %s", username)
            user = session.query(db.User).get(username)
            session.delete(user)
        if selection:
            flash("Account(s) %s deleted" % ', '.join(
                    '"%s"' % u.encode('utf-8') for u in selection), msg=True)
    if 'lock' in request.values:
        for username in selection:
            log.debug("Locking user %s", username)
            user = session.query(db.User).get(username)
            user.locked_out = True
        if selection:
            flash("Account(s) %s locked-out" % ', '.join(
                    '"%s"' % u.encode('utf-8') for u in selection), msg=True)
    if 'unlock' in request.values:
        for username in selection:
            log.debug("Un-locking user %s", username)
            user = session.query(db.User).get(username)
            user.locked_out = False
        if selection:
            flash("Account(s) %s un-locked" % ', '.join(
                    '"%s"' % u.encode('utf-8') for u in selection), msg=True)
    session.commit()
    accounts = session.query(db.User).all()
    return generate_template('accounts/index.html', accounts=accounts)

def new(request):
    if request.method != 'POST':
        return generate_template('accounts/new.html', password=gen_salt(8))

    username = request.values.get('username')
    email = request.values.get('email')
    password = request.values.get('password')
    is_admin = request.values.get('admin') == 'yes'

    if not username or not email or not password:
        flash("All fields are required!", error=True)
        return generate_template("accounts/new.html", formfill=request.values)

    if session.query(db.User).filter_by(username=username).first():
        flash("This username is already taken!", error=True)
        return generate_template("accounts/new.html", formfill=request.values)
    if session.query(db.User).filter_by(email=email).first():
        flash("This email adderss is already in use! Please choose a different "
              "one.", error=True)
        return generate_template("accounts/new.html", formfill=request.values)

#    user = db.User(username, password, is_admin)
#    user.confirmed = False
    change = db.Change({'username': username, 'password': password,
                        'is_admin': is_admin, 'email': email})
    session.add(change)
    session.commit()
    request.notification.sendmail("Account Create Confirmation",
                                  'new_account.txt', {'change': change},
                                  email)
    flash("An email message was sent to %s in order to confirm the email "
          "address. Until confirmed, your the account won't be created at "
          "all." % email)
    return redirect(url_for('accounts.index'))
