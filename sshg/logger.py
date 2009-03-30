# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import logging
from twisted.python.log import PythonLoggingObserver
from twisted.internet import defer

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)-5.5s: %(message)s'
)

class PythonLogObserver(PythonLoggingObserver):

    def __init__(self, logger_name='sshg'):
        self.logger = logging.getLogger("sshg")

    def emit(self, event_dict):
        def emit():
            PythonLoggingObserver.emit(self, event_dict)
        return defer.maybeDeferred(emit)


class Logging(object):
    def __init__(self, logger_name='sshg'):
        self.logger = logging.getLogger(logger_name)

    def debug(self, msg, *args, **kwargs):
        defer.maybeDeferred(self.logger.debug, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        defer.maybeDeferred(self.logger.info, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        defer.maybeDeferred(self.logger.warning, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        defer.maybeDeferred(self.logger.error, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        defer.maybeDeferred(self.logger.critical, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        defer.maybeDeferred(self.logger.exception, msg, *args, **kwargs)


def getLogger(logger_name):
    return Logging(logger_name)
