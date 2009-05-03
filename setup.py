#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from setuptools import setup
import sshg

setup(name=sshg.__package__,
      version=sshg.__version__,
      author=sshg.__author__,
      author_email=sshg.__email__,
      url=sshg.__url__,
      download_url='http://python.org/pypi/%s' % sshg.__package__,
      description=sshg.__summary__,
      long_description=sshg.__description__,
      license=sshg.__license__,
      platforms="OS Independent - Anywhere Twisted and Mercurial is known to run.",
      keywords = "Twisted Mercurial SSH ACL HG",
      packages=['sshg'],
      install_requires = ['simplejson', 'SQLAlchemy', 'decorator'],
      package_data={
          'sshg': ['upgrades/*.cfg']
      },
      classifiers=[
          'Development Status :: 5 - Alpha',
          'Environment :: Web Environment',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Utilities',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ]
)
