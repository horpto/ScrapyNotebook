#!/bin/env python
# -*- encoding: utf-8 -*-
"""Scrapy RPyC Extension"""
from __future__ import print_function

from twisted.internet import protocol, reactor

from scrapy.exceptions import NotConfigured
from scrapy import log, signals
from scrapy.utils.reactor import listen_tcp

from rpyc.core import Connection, Channel
from rpyc.core.stream import Stream
from rpyc.core.service import SlaveService, ModuleNamespace

from time import sleep
import inspect

from ScrapyNotebook.utils import get_vars, mark_source_method

class RPyCAsyncStream(Stream):

    __slots__ = ("transport", "buffer",)
    def __init__(self, protocol):
        Stream.__init__(self)
        self.buffer = ""
        self.transport = protocol.transport

    @property
    def len(self):
        return len(self.buffer)

    def close(self):
        pass

    @property
    def closed(self):
        return len(self.buffer) > 0

    def poll(self, timeout):
        for i in range(10):
            if self.buffer:
                return True
            sleep(timeout/10.0)
        return False

    def write(self, data):
        self.transport.writeSomeData(data)

    def dataReceived(self, data):
        self.buffer += data

    def read(self, count):
        if len(self.buffer) < count:
            raise EOFError("Not enough data")

        res, self.buffer = self.buffer[:count],  self.buffer[count:]
        return res


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
        src = getattr(obj, self.SRC_LABEL_ATTR, None)
        if src:
            return src

        attr = {name: getattr(obj, name) for name in dir(obj)}
        ischanged = any(getattr(val, self.SRC_LABEL_ATTR, False)
                        for val in attr.itervalues())
        if (inspect.isroutine(obj) or not ischanged):
            return self.cut_excess(inspect.getsource(obj))

        if inspect.ismodule(obj):
            return self._join_functions(obj, attr)
        if inspect.isclass(obj):
            return self._get_source_class(obj, attr)
        
        return self._get_source_class(type(obj), attr)

    def _get_source_class(self, obj, attr=None):
        if attr is None:
            attr = {name: getattr(obj, name) for name in dir(obj)}
        pat = "class {cls_name}({parents}):\n" \
              "    {defs}\n"
        defs = self._join_functions(obj, attr, sep='\n    ',
                                       in_func_sep='\n    ')
        return pat.format(cls_name=obj.__name__,
                          parents=', '.join(t.__name__ for t in obj.__mro__),
                          defs=defs,)

    def _join_functions(self, obj, attr=None, sep='\n\n', in_func_sep='\n'):
        if attr is None:
            attr = {name: getattr(obj, name) for name in dir(obj)}

        defs = []
        for name, val in attr.iteritems():
            spec = getattr(val, self.SRC_LABEL_ATTR, False)

            if inspect.isroutine(val) and not spec:
                try:
                    spec = self.cut_excess(inspect.getsource(val))
                except (TypeError, IOError):
                    spec = str(val)
            else:
                if not spec: 
                    spec = val
                spec = '{} = {}'.format(name, str(spec))
            defs.append(in_func_sep.join(spec.splitlines()))
        
        return sep.join(defs)

    @staticmethod
    def cut_excess(func_source, exclude=None):
        slocs = func_source.expandtabs().splitlines()
        spaces = len(slocs[0]) - len(slocs[0].lstrip())

        if not spaces:
            return func_source
        if exclude is None:
            return '\n'.join(s and s[spaces:] for s in slocs)
        exclude = set(exclude) if isinstance(exclude, (tuple, list)) else exclude

        pred = lambda s: not (s and s[spaces:] in exclude)
        slocs = '\n'.join(s[spaces:] for s in slocs if pred(s))
    
        return slocs

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
