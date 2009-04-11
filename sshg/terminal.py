# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from twisted.internet import reactor, task
from twisted.conch.insults import insults, window

from sshg import logger

log = logger.getLogger(__name__)

class DemoTerminal(insults.TerminalProtocol):
    width = 80
    height = 24

    def _draw(self):
        self.window.draw(self.width, self.height, self.terminal)

    def _redraw(self):
        self.window.filthy()
        self._draw()

    def _schedule(self, f):
        reactor.callLater(0, f)

    def connectionMade(self):
        self.terminal.eraseDisplay()
        self.terminal.resetPrivateModes([insults.privateModes.CURSOR_MODE])

        self.window = window.TopWindow(self._draw, self._schedule)
        self.output = window.TextOutput((15, 1))
        self.input = window.TextInput(15, self._setText)
        self.select1 = window.Selection(map(str, range(100)), self._setText, 10)
        self.select2 = window.Selection(map(str, range(200, 300)), self._setText, 10)
        self.button = window.Button("Clear", self._clear)
        #self.canvas = DrawableCanvas()

        hbox = window.HBox()
        hbox.addChild(self.input)
        hbox.addChild(self.output)
        hbox.addChild(window.Border(self.button))
        hbox.addChild(window.Border(self.select1))
        hbox.addChild(window.Border(self.select2))

        t1 = window.TextOutputArea(longLines=window.TextOutputArea.WRAP)
        t2 = window.TextOutputArea(longLines=window.TextOutputArea.TRUNCATE)
        t3 = window.TextOutputArea(longLines=window.TextOutputArea.TRUNCATE)
        t4 = window.TextOutputArea(longLines=window.TextOutputArea.TRUNCATE)
        for _t in t1, t2, t3, t4:
            _t.setText((('This is a very long string.  ' * 3) + '\n') * 3)

        vp = window.Viewport(t3)
        d = [1]
        def spin():
            vp.xOffset += d[0]
            if vp.xOffset == 0 or vp.xOffset == 25:
                d[0] *= -1
        self.call = task.LoopingCall(spin)
        self.call.start(0.25, now=False)
        hbox.addChild(window.Border(vp))

        vp2 = window.ScrolledArea(t4)
        hbox.addChild(vp2)

        texts = window.VBox()
        texts.addChild(window.Border(t1))
        texts.addChild(window.Border(t2))

        areas = window.HBox()
        #areas.addChild(window.Border(self.canvas))
        areas.addChild(texts)

        vbox = window.VBox()
        vbox.addChild(hbox)
        vbox.addChild(areas)
        self.window.addChild(vbox)
        self.terminalSize(self.width, self.height)

    def connectionLost(self, reason):
        self.call.stop()
        insults.TerminalProtocol.connectionLost(self, reason)

    def terminalSize(self, width, height):
        self.width = width
        self.height = height
        self.terminal.eraseDisplay()
        self._redraw()


    def keystrokeReceived(self, keyID, modifier):
        self.window.keystrokeReceived(keyID, modifier)

    def _clear(self):
        pass
        #self.canvas.clear()

    def _setText(self, text):
        self.input.setText('')
        self.output.setText(text)


class AdminTerminal(insults.TerminalProtocol):
    width = 80
    height = 24

    def _draw(self):
        self.window.draw(self.width, self.height, self.terminal)

    def _schedule(self, f):
        reactor.callLater(0, f)

    def _redraw(self):
        self.window.filthy()
        self._draw()

    def connectionLost(self, reason):
        insults.TerminalProtocol.connectionLost(self, reason)

    def terminalSize(self, width, height):
        self.width = width
        self.height = height
        self.terminal.eraseDisplay()
        self._redraw()

    def connectionMade(self):
        self.terminal.eraseDisplay()
        self.terminal.resetPrivateModes([insults.privateModes.CURSOR_MODE])

        self.window = window.TopWindow(self._draw, self._schedule)

    def keystrokeReceived(self, keyID, modifier):
        log.debug("keystrokeReceived: %s -> %r; Modifier: %s -> %r",
                  keyID, keyID, modifier, modifier)
        if keyID in ('\x03', '\x04'):
            self.terminal.loseConnection()
        else:
            self.window.keystrokeReceived(keyID, modifier)
