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
      platforms="OS Independent - Anywhere Python and ISPMan is known to run.",
      install_requires = ['Babel'],
      keywords = "ISPMan Control Panel",
      packages=['sshg'],
#      package_data={
#        'tracext.dm': [
#            'templates/*.html',
#            'htdocs/css/*.css',
#            'htdocs/img/*.png',
#            'htdocs/img/*.gif',
#            'htdocs/js/*.js',
#        ]
#      },
      message_extractors = {
        'sshg': [
            ('**.py', 'python', None)
        ],
        'flex': [
            ('**.as', 'sshg.utils.translations:extract_actionscript', None),
            ('**.mxml', 'sshg.utils.translations:extract_mxml', {
                'attrs': [
                    u'label', u'text', u'title', u'headerText', u'prompt']}),
        ]
      },
      entry_points = {
        'distutils.commands': [
            'extract = babel.messages.frontend:extract_messages',
            'init = babel.messages.frontend:init_catalog',
            'compile = babel.messages.frontend:compile_catalog',
            'update = babel.messages.frontend:update_catalog'
        ]
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
