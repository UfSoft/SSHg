# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from sshg.web.views import *
from sshg.utils.crypto import gen_pwhash

log = logger.getLogger(__name__)

def login(request):
    if request.method== "POST":
        username = request.values.get('username')
        password = request.values.get('password')
        user = session.query(db.User).filter_by(username=username).first()
        if not user:
            flash("User is not known.", error=True)
            return generate_template("account/login.html",
                                     formfill=request.values)
        if not user.authenticate(password):
            flash("Authentication failed.", error=True)
            return generate_template("account/login.html",
                                     formfill=request.values)
        request.login(user, permanent=True)
    if request.user and not request.user.is_manager:
        return redirect(url_for('account.prefs'))
    elif request.user and request.user.is_manager:
        return redirect(url_for('admin'))
    return generate_template("account/login.html")


def logout(request):
    request.session.clear()
    return redirect(url_for('admin'))

def preferences(request):
    """Return the user configurable prefences"""
    if request.method == 'POST':
        new_email = request.values.get('email')
        new_password = request.values.get('password')
        new_password_confirm = request.values.get('password_confirm')
        if new_password and not new_password_confirm:
            flash("You need to confirm your password", error=True)
            return generate_template('account/preferences.html',
                                     user=request.user,
                                     formfill=request.values)
        elif not new_password and new_password_confirm:
            flash("Can't confirm an empty password", error=True)
            return generate_template('account/preferences.html',
                                     user=request.user,
                                     formfill=request.values)
        elif new_password and new_password_confirm:
            if new_password != new_password_confirm:
                flash("Passwords do not match", error=True)
                return generate_template('account/preferences.html',
                                         user=request.user,
                                         formfill=request.values)
            request.user.password = new_password
            session.commit()
        if new_email != request.user.email:
            email_exists = session.query(db.User).filter_by(
                email = new_email).filter(
                    db.User.username != request.user.username).first()
            if email_exists:
                flash("This email address is already taken by another user "
                      "other than you. Please choose a different one.",
                      error=True)
                return generate_template('account/preferences.html',
                                         user=request.user,
                                         formfill=request.values)
            change = db.Change({'email': new_email})
            change.owner = request.user
            session.add(change)
            session.commit()
            request.notification.sendmail("Account Change Confirmation",
                                          'email_change.txt',
                                          {'change': change}, new_email)
            flash("An email message was sent to %s in order to confirm the "
                  "address. Until confirmed, your old address is still in "
                  "use." % new_email)
        if request.values.get('delete_keys'):
            for key in request.values.getlist('sel'):
                pubkey = session.query(db.PublicKey).get(key)
                session.delete(pubkey)
            session.commit()
        new_keys = request.values.get('new_keys')
        for line, key_contents in enumerate(new_keys.splitlines()):
            log.debug("Line: %d  Contents: %s", line, key_contents)
            pubkey = db.PublicKey(key_contents)
            key_exists = session.query(db.PublicKey).get(pubkey.key)
            if key_exists:
                flash("The public-key on line %d already exists" % (line+1),
                      error=True)
            else:
                request.user.keys.append(pubkey)
        session.commit()
        return redirect(url_for('account.prefs'))
    return generate_template('account/preferences.html', user=request.user)

def reset(request):
    if request.user:
        flash("You're logged in! No need to reset the password. Just change it "
              "on your preferences.", error=True)
        return redirect(url_for('account.prefs'))
    if request.method == 'POST':
        email = request.values.get('email')
        new_password = request.values.get('password')
        new_password_confirm = request.values.get('password_confirm')
        if not email:
            flash("In order to reset a password, you need to provide an email "
                  "address", error=True)
            return generate_template('account/reset.html')
        user = session.query(db.User).filter_by(email=email).first()
        if not user:
            flash("No user is known by this email address", error=True)
            return generate_template('account/reset.html')
        if new_password != new_password_confirm:
            flash("The passwords do not match", error=True)
            return generate_template('account/reset.html',
                                     formfill=request.values)
        change = db.Change({'password': gen_pwhash(new_password)})
        change.owner = user
        session.add(change)
        session.commit()
        request.notification.sendmail("Account Change Confirmation",
                                      'password_reset.txt',
                                      {'change': change}, email)
        flash("An email message was sent to %s in order to confirm the "
              "password change. Until confirmed, your old password is still in "
              "use." % email)
    return generate_template('account/reset.html',
                             email=request.values.get('email', None))


def confirm(request, confirm_hash=None):
    if request.user and request.user.changes.count() == 0:
        flash("There are no changes for you which need to be confirmed")
        return redirect(url_for('admin'))
    confirm_hash = request.values.get('confirm_hash', confirm_hash)
    if not confirm_hash:
        flash("Please insert the hash you were given", request.method == 'POST')
        return generate_template('account/confirm.html')
    else:
        change = session.query(db.Change).get(confirm_hash)

        if not change.owner:
            new_account = db.User(**change.changes)
            new_account.session = db.Session()
            session.add(new_account)
            session.delete(change)
            flash("Account created. Please reset your password now.", msg=True)
            session.commit()
            return redirect(url_for('account.reset', email='pa@ufsoft.org'))

        for key, value in change.changes.iteritems():
            setattr(change.owner, key, value)
        session.delete(change)
        session.commit()
        flash("The requested change(s) were confirmed.", msg=True)
        return redirect(url_for('admin'))
