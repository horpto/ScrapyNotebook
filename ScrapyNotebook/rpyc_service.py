#!/bin/env python
# -*- encoding: utf-8 -*-
"""Scrapy RPyC Extension"""

from twisted.internet import protocol, reactor

from scrapy.exceptions import NotConfigured
from scrapy import log, signals
from scrapy.utils.reactor import listen_tcp

from rpyc.core import Connection, Channel
from rpyc.core.service import SlaveService, ModuleNamespace

from ScrapyNotebook.utils.sources import (mark_source_method,
                                          get_source)
from ScrapyNotebook.utils.scrapy_utils import get_vars
from ScrapyNotebook.utils.rpyc_utils import RPyCAsyncStream

class ScrapyService(SlaveService):

    __slots__ = ("exposed_namespace",)
    def __init__(self, conn):
        super(ScrapyService, self).__init__(conn)
        self.exposed_namespace = {}

    def on_connect(self):
        self._conn._config.update(dict(
            allow_all_attrs = True,
            allow_pickle = True,
            allow_getattr = True,
            allow_setattr = True,
            allow_delattr = True,
            import_custom_exceptions = True,
            instantiate_custom_exceptions = True,
            instantiate_oldstyle_exceptions = True,
        ))
        # shortcuts
        self._conn.modules = ModuleNamespace(self._conn.root.getmodule)
        self._conn.eval = self._conn.root.eval
        self._conn.execute = self._conn.root.execute
        self._conn.namespace = self._conn.root.namespace
        from rpyc.lib.compat import is_py3k
        if is_py3k:
            self._conn.builtin = self._conn.modules.builtins
        else:
            self._conn.builtin = self._conn.modules.__builtin__
        self._conn.builtins = self._conn.builtin

    def on_disconnect(self):
        SlaveService.on_disconnect(self)

    def extend(self, variables):
        self.exposed_namespace.update(variables)

    def exposed_get_source(self, obj):
        return get_source(obj)

    def exposed_set_source(self, obj, method_name, src):
        func = mark_source_method(obj, method_name, src)
        reactor.callFromThread(setattr, obj, method_name, func)


class RPyCProtocol(protocol.Protocol):
    stream = RPyCAsyncStream

    def __init__(self, conn, service, channel=Channel, rpyc_vars=None):
        self.conn = conn
        self.service = service
        self.channel = channel
        if rpyc_vars is None:
            rpyc_vars = {}
        self.vars = rpyc_vars

    def connectionMade(self):
        self.stream = self.stream(self)
        self.channel = self.channel(self.stream)
        self.conn = self.conn(ScrapyService, self.channel, _lazy=True)

        self.conn._local_root.extend(self.vars) # это
        reactor.callInThread(self._body) # и это именно в таком порядке

    def _body(self):
        self.conn._init_service()
        self.conn.serve_all()

    def dataReceived(self, data):
        self.stream.dataReceived(data)

    def connectionLost(self, reason=protocol.connectionDone):
        if hasattr(self, "conn"):
            self.conn.close()


class RPyCFactory(protocol.ServerFactory):
    """
    Generates RPyCProtocol instances.
    """

    protocol = RPyCProtocol
    service = ScrapyService

    def __init__(self, crawler):
        if not crawler.settings.getbool('RPYCSERVICE_ENABLED'):
            raise NotConfigured
        self.crawler = crawler
        self.noisy = False
        self.portrange = [int(x) for x in crawler.settings.getlist('RPYCSERVICE_PORT')]
        self.host = crawler.settings['RPYCSERVICE_HOST']
        self.crawler.signals.connect(self.start_listening, signals.engine_started)
        self.crawler.signals.connect(self.stop_listening, signals.engine_stopped)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def start_listening(self):
        self.port = listen_tcp(self.portrange, self.host, self)
        h = self.port.getHost()
        log.msg(format="RPyC service listening on %(host)s:%(port)d",
                level=log.DEBUG, host=h.host, port=h.port)

    def stop_listening(self):
        self.port.stopListening()

    def buildProtocol(self, addr):
        rpyc_vars = get_vars(self.crawler)
        return self.protocol(Connection, self.service, rpyc_vars=rpyc_vars)
