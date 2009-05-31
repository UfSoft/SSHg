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

    if 'delete' in request.values:
        selection = request.values.getlist('sel')
        for reponame in selection:
            repo = session.query(db.Repository).get(reponame)
            session.delete(repo)
            flash("The repository by the name %s is no "
                  "longer managed." % reponame, msg=True)
        session.commit()

    repos = request.user.manages.all()
    return generate_template('repos/index.html', repos=repos)

def new(request):
    if request.method != 'POST':
        return generate_template('repos/new.html')

    required_fields = []
    reponame = request.values.get('reponame', '').strip()
    if not reponame:
        required_fields.append('repository name')
    repopath = request.values.get('repopath', '').rstrip('/')
    if not repopath:
        required_fields.append('repository path')
    if required_fields:
        for field in required_fields:
            flash("The %s is required." % field, error=True)
        return generate_template('repos/new.html', formfill=request.values)
    exists = session.query(db.Repository).filter(
        db.or_(db.Repository.name==reponame,
               db.Repository.path==repopath)).first()
    if exists:
        if exists.name == reponame:
            flash("A Repository by that name already exists. Please choose "
                  "a different one.", error=True)
        elif exists.path == repopath:
            flash("A Repository with this path is already managed.", error=True)
        return generate_template('repos/new.html', formfill=request.values)

    quota = int(request.values.get('quota', '0'))
    try:
        repo = db.Repository(reponame, repopath, quota)
    except Exception, err:
        flash(err.message, error=True)
        return generate_template('repos/new.html', formfill=request.values)
    session.add(repo)
    session.commit()
    flash("Repository added.", msg=True)
    return redirect(url_for('repos.index'))

def edit(request, reponame):
    repo = session.query(db.Repository).get(reponame)

    if request.method != 'POST':
        users = session.query(db.User).all()
        return generate_template('repos/edit.html', repo=repo, users=users)

    if 'update' in request.values:
        repo.quota = int(request.values.get('quota', repo.quota))
        flash("Updated repository details", msg=True)

    elif 'update_users' in request.values:
        deleted_users = []
        added_users = []
        users = request.values.getlist('users')
        log.debug('Users: %s', users)
        for idx, user in enumerate(repo.users):
            if user.username in users:
                users.pop(users.index(user.username))
            else:
                deleted_users.append(user)

        if users:
            for username in users:
                added_users.append(username)
                user = session.query(db.User).get(username)
                repo.users.append(user)
            session.commit()

        if deleted_users:
            for user in deleted_users:
                repo.users.pop(repo.users.index(user))
            session.commit()
            flash("Removed users: %s" % ', '.join([u.username for u in
                                                   deleted_users]), msg=True)

        if added_users:
            flash("Added users: %s" % ', '.join(added_users), msg=True)

        managers = request.values.getlist('managers')
        deleted_managers = []
        added_managers = []
        log.debug('Managers: %s -- %s', managers, repo.managers)

        for manager in repo.managers:
            log.debug("Processing manager %s", manager)
            if manager.username in managers:
                managers.pop(managers.index(manager.username))
            else:
                deleted_managers.append(manager)
                session.commit()

        if managers:
            for username in managers:
                added_managers.append(username)
                user = session.query(db.User).get(username)
                repo.managers.append(user)
            session.commit()

        if deleted_managers:
            for manager in deleted_managers:
                repo.managers.pop(repo.managers.index(manager))
            session.commit()
            flash("Removed managers: %s" % ', '.join([m.username for m in
                                                      deleted_managers]),
                  msg=True)
        if added_managers:
            flash("Added managers: %s" % ', '.join(added_managers), msg=True)


    users = session.query(db.User).all()
    return generate_template('repos/edit.html', repo=repo, users=users)
