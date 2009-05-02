# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

import re
from email.charset import Charset, BASE64
from StringIO import StringIO
from twisted.internet import defer, reactor
from twisted.internet.ssl import ClientContextFactory
from twisted.mail.smtp import ESMTPSenderFactory

from OpenSSL.SSL import SSLv3_METHOD, TLSv1_METHOD

from sshg.web.utils import generate_template


RECRLF = re.compile("\r?\n")
MAXHEADERLEN = 76

class NotificationSystem(object):

    def __init__(self):
        from sshg import config
        cn = config.notification
        if not cn.smtp_from and not cn.reply_to:
            self.enabled = False

        self._charset = Charset()
        self._charset.input_charset = 'utf-8'
        self._charset.header_encoding = BASE64
        self._charset.body_encoding = BASE64
        self._charset.output_charset = 'utf-8'
        self._charset.input_codec = 'utf-8'
        self._charset.output_codec = 'utf-8'

    def _format_header(self, key, name, email=None):
        from email.header import Header
        maxlength = MAXHEADERLEN-(len(key)+2)
        # Do not sent ridiculous short headers
        if maxlength < 10:
            raise Exception("Header length is too short")
        try:
            tmp = name.encode('ascii')
            header = Header(tmp, 'ascii', maxlinelen=maxlength)
        except UnicodeEncodeError:
            header = Header(name, self._charset, maxlinelen=maxlength)
        if not email:
            return header
        return '"%s" <%s>' % (header, email)

    def _add_headers(self, msg, headers):
        for h in headers:
            msg[h] = self._encode_header(h, headers[h])

    def _encode_header(self, key, value):
        if isinstance(value, tuple):
            return self._format_header(key, value[0], value[1])
        if isinstance(value, list):
            items = []
            for v in value:
                items.append(self._encode_header(v))
            return ',\n\t'.join(items)
#        mo = self.longaddr_re.match(value)
#        if mo:
#            return self.format_header(key, mo.group(1), mo.group(2))
        return self._format_header(key, value)

    def sendmail(self, subject, template, data, to, mime_headers={}):
        from email.mime.text import MIMEText
        from email.utils import formatdate
        from sshg import config
        stream = generate_template('email/%s' % template, **data)
        body = stream.render('text')
#        body = content
        headers = {}
        headers['X-Mailer'] = 'SSHg %s, by UfSoft.org'
        headers['X-Screener-Version'] = '0.1'
#        headers['X-URL']
        headers['Precedence'] = 'bulk'
        headers['Auto-Submitted'] = 'auto-generated'
        headers['Subject'] = subject
        headers['From'] = (config.notification.from_name,
                           config.notification.smtp_from)
        headers['Reply-To'] = config.notification.reply_to

#        recipients = torcpts
#        headers['To'] = ', '.join(torcpts)
        headers['To'] = to
        headers['Date'] = formatdate()
        if not self._charset.body_encoding:
            try:
                dummy = body.encode('ascii')
            except UnicodeDecodeError:
                raise Exception("Failed to encode body")
        msg = MIMEText(body, 'plain')
        # Message class computes the wrong type from MIMEText constructor,
        # which does not take a Charset object as initializer. Reset the
        # encoding type to force a new, valid evaluation
        del msg['Content-Transfer-Encoding']
        msg.set_charset(self._charset)
        self._add_headers(msg, headers);
        self._add_headers(msg, mime_headers);
        msgtext = msg.as_string()
        # Ensure the message complies with RFC2822: use CRLF line endings
        msgtext = CRLF = '\r\n'.join(RECRLF.split(msgtext))
        self._sendmail(to, StringIO(msgtext))

    def _sendmail(self, to, email_msg_file):
        from sshg import config
        deferred = defer.Deferred()
        contextFactory = ClientContextFactory()
        contextFactory.method = SSLv3_METHOD
        if config.notification.smtp_user and config.notification.smtp_pass:
            requireAuthentication = True
        else:
            requireAuthentication = False

        sender_factory = ESMTPSenderFactory(
            config.notification.smtp_user,
            config.notification.smtp_pass,
            config.notification.smtp_from,
            to,
            email_msg_file,
            deferred,
            retries=5,
            timeout=30,
            contextFactory=contextFactory,
            heloFallback=False,
            requireAuthentication=requireAuthentication,
            requireTransportSecurity=config.notification.use_tls
        )
        reactor.connectTCP(config.notification.smtp_server,
                           config.notification.smtp_port, sender_factory)
        return deferred
