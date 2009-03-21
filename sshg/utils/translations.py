# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
"""
    sshg.utils.babel
    ~~~~~~~~~~~~~~~~

    This module holds translations message extraction methods for actionscript
    and flex.

    :copyright: © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
    :license: BSD, see LICENSE for more details.
"""

from xml.parsers import expat
from xml.etree import ElementTree
from StringIO import StringIO
from babel.messages.extract import extract_javascript

# ActionScript is a superset of Javascript, let's use the javascript extractor
extract_actionscript = extract_javascript

class ParseError(Exception):
    pass

class MXMLParser(object):

    def __init__(self, source):
        self.source = source

        parser = expat.ParserCreate()
        parser.buffer_text = True
        parser.returns_unicode = True
        parser.ordered_attributes = True
        parser.StartElementHandler = self._handle_start
        parser.EndElementHandler = self._handle_end
        parser.CharacterDataHandler = self._handle_data

        if not hasattr(parser, 'CurrentLineNumber'):
            self._getpos = self._getpos_unknown

        self.expat = parser
        self._queue = []
        self._elems = []

    def parse(self):
        try:
            bufsize = 4 * 1024 # 4K
            done = False
            while not done and len(self._queue) == 0:
                data = self.source.read(bufsize)
                if data == '': # end of data
                    if hasattr(self, 'expat'):
                        self.expat.Parse('', True)
                        del self.expat # get rid of circular references
                    done = True
                else:
                    if isinstance(data, unicode):
                        data = data.encode('utf-8')
                    self.expat.Parse(data, False)
                for event in self._queue:
                    yield event
                self._queue = []
                if done:
                    break
        except expat.ExpatError, e:
            raise ParseError(str(e))

    def _handle_start(self, tag, attrib):
        _attrib = {}
        while attrib:
            key = attrib.pop(0)
            value = attrib.pop(0)
            _attrib[key] = value
        self._elems.append(ElementTree.Element(tag, _attrib))

    def _handle_end(self, tag):
        if self._elems:
            self._queue.append((self._elems.pop(), self._getpos()))

    def _handle_data(self, text):
        if self._elems:
            if self._elems[-1].text:
                self._elems[-1].text += text.encode('utf-8')
            else:
                self._elems[-1].text = text.encode('utf-8')

    def _getpos(self):
        return (self.expat.CurrentLineNumber,
                self.expat.CurrentColumnNumber)

    def _getpos_unknown(self):
        return (-1, -1)

def extract_mxml(fileobj, keywords, comment_tags, options):
    for elem, pos in MXMLParser(fileobj).parse():
        if elem.tag == 'mx:Script':
            for lineno, funcname, message, comments in \
                            extract_javascript(StringIO(elem.text), keywords,
                                                 comment_tags, options):
                yield pos[0]+lineno, funcname, message, comments
        else:
            attrib = None
            for attr in options.get('attrs', []):
                if elem.get(attr):
                    attrib = attr
            if attrib:
                if elem.attrib[attrib].startswith('{') and \
                    elem.attrib[attrib].endswith('}'):
                    for _, funcname, message, comments in extract_actionscript(
                                        StringIO(elem.attrib[attrib][1:-1]),
                                        keywords, comment_tags, options):
                        yield pos[0], funcname, message, comments
