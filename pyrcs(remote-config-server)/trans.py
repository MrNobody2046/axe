#coding:utf-8
import os
import socket
import time
import cPickle
from cStringIO import StringIO
import importlib


"""
python remote config server
服务端集中存放配置，客户端通过tcp读取配置

客户端的配置使用起来和普通python模块没有区别
eg：
from rcs.client import client
client.host = "1.2.3.4"
conf = client.get_remote_conf("mysql")
print conf.host
print conf.password


"""

class Data(object):
    pass


class Transfer(object):

    def __init__(self):
        pass




def pack(obj):
    if obj:
        return cPickle.dumps(obj)
    else:
        return cPickle.dumps(None)


def unpack(data):
    try:
        return cPickle.loads(data)
    except EOFError:
        pass


def recv_data(socket):
    revfile = StringIO()
    while True:
        buf = socket.recv(BUFFER_SIZE)
        if buf and buf[-MSG_EOF_LENGTH:] == MSG_EOF:
            revfile.write(buf[:-MSG_EOF_LENGTH])
            # revfile.write(buf.replace(MSG_EOF,''))
            break
        else:
            revfile.write(buf)
    revfile.seek(0)
    data = revfile.read()
    return unpack(data)


def send_data(socket, data):
    sendfile = StringIO()
    packed_data = pack(data)
    sendfile.write(packed_data)
    sendfile.write(MSG_EOF)
    sendfile.seek(0)
    while True:
        buf = sendfile.read(BUFFER_SIZE)
        if buf:
            socket.send(buf)
        else:
            break


class Configer():

    def __init__(self, host='127.0.0.1'):
        self._host = host

    def __connect__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._addr = (self._host, Port)
        self._socket.connect(self._addr)

    def __getattr__(self, attr):
        if attr.startswith('_'):
            return self.__getattribute__(attr)
        return self.__post__(attr)

    def __post__(self, attr):
        self.__connect__()
        send_data(self._socket, attr)
        flag, res = recv_data(self._socket)
        self._socket.close()
        if flag:
            return res
        else:
            raise Exception("no attribute '%s'" % attr)
        return res


class ConfServer():

    def __call__(self, filename):
        self.config_file = filename
        self.mtime = self.get_mtime(filename)
        self.conf = self.import_conf(filename)
        joinall([spawn(job) for job in [self.server, self.reload_conf]])

    def get_mtime(self, filename):
        return os.stat(filename).st_mtime

    def import_conf(self, filename):
        return importlib.import_module(filename.replace('.py', ''))

    def reload_conf(self):
        while True:
            new_mtime = self.get_mtime(self.config_file)
            if new_mtime != self.mtime:
                self.mtime = new_mtime
                print "Reload."
                try:
                    self.conf = reload(self.conf)
                except Exception, e:
                    print "reload error,%r" % e
            time.sleep(0.5)

    def read(self, attr):
        return getattr(self.conf, attr)

    def server(self):
        def _proxy(socket, address):
            attr = recv_data(socket)
            res = self.handle(attr)
            send_data(socket, res)
        server = StreamServer(
            ('0.0.0.0', 12345), _proxy)  # creates a new server
        server.serve_forever()

    def handle(self, attr):
        try:
            return True, self.read(attr)
        except Exception, e:
            return False, repr(e)
