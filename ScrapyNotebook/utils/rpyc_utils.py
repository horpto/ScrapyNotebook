#!/bin/env python
# -*- encoding: utf-8 -*-

import rpyc
from rpyc.core.stream import (SocketStream, Stream)
from time import sleep

import logging
logger = logging.getLogger()

class LoggableSocketStream(SocketStream):

    def read(self, count):
        buf = SocketStream.read(self, count)
        logger.debug("Read: {}{}".format(buf, self.get_ending(buf)))
        return buf

    def write(self, data):
        logger.debug("Write: {}{}".format(data, self.get_ending(data)))
        SocketStream.write(self, data)

    @staticmethod
    def get_ending(buf):
        return '' if buf.endswith('\n') else '\n'


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

def is_remote(obj):
    return isinstance(obj, (rpyc.core.netref.BaseNetref,
                            rpyc.core.netref.NetrefMetaclass))
