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
    pass
