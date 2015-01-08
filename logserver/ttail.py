#!/usr/bin/env python
import time
from subprocess import *
import argparse
import fcntl
import select
import os
import Queue


class File(object):
    NORMAL = 1
    SSH = 2

    def __init__(self, name):
        self.name = name
        if name.find(":") != -1:
            host, remote_file = fd.split(':', 1)
            self.basename = os.path.basename(remote_file)
            self.fd = Popen(["ssh", "-o BatchMode=yes", host, "tail", "-f", remote_file],
                            stdin=PIPE, stdout=PIPE, close_fds=True)
            self._t = self.SSH
        else:
            self._t = self.NORMAL
            self.fd = open(name)
            self.basename = os.path.basename(name)
        self._buffer = ""
        self.queue = Queue.Queue()

    @property
    def file_name(self):
        return self.basename

    def __hash__(self):
        return self.fd.__hash__()

    def _read_line(self):
        line = ''
        fileno = self.fd.fileno()
        fl = fcntl.fcntl(fileno, fcntl.F_GETFL)
        fcntl.fcntl(fileno, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            self._buffer += self.fd.read(1)
            while self._buffer[-1] != '\n':
                self._buffer += self.fd.read(1)
            fcntl.fcntl(fileno, fcntl.F_SETFL, fl)
            return True
        except IOError:
            fcntl.fcntl(fileno, fcntl.F_SETFL, fl)
            return False

    def read(self):
        if self._t != self.NORMAL:
            pipe = self.fd
            pipe.poll()
        if self._read_line():
            return self._buffer
        else:
            return ""


class CH(object):
    def __init__(self, m):
        self.m = m

    def __hash__(self):
        return self.m.__hash__()


a = 1
s = "sadasd"
print a.__hash__()
print s.__hash__()

someset = {CH(1), CH(2), CH(333)}
print CH(1) in someset
print someset
1 / 0


class LineStream():
    def __init__(self, files):
        self.files = files
        self.file_list = [f.fd for f in files]

    def run(self):
        buffers = {}
        while len(self.file_list) > 0:
            print "loop"
            rlist, _, _ = select.select(self.file_list, [], [])
            print rlist, _, _
            wait = 0
            for readfile in rlist:
                readfile = self.files[readfile]
                if isinstance(readfile, basestring):
                    newline, full = self.readline(readfile)
                    if readfile in buffers:
                        buffers[readfile] += newline
                    else:
                        buffers[readfile] = newline
                    if buffers[readfile] and full:
                        print "%s::%s" % (self.files[readfile],
                                          buffers[readfile]),
                        del buffers[readfile]
                    elif not buffers[readfile] and wait == 0:
                        wait = 1
                else:
                    # for ssh pipes
                    wait = 2
                    pipe = self.files[readfile][0]
                    pipe.poll()
                    newline, full = self.readline(readfile)
                    if readfile in buffers:
                        buffers[readfile] += newline
                    else:
                        buffers[readfile] = newline
                    if buffers[readfile] and full:
                        print "%s::%s" % (self.files[readfile][1],
                                          buffers[readfile]),
                        del buffers[readfile]
                    if pipe.returncode:
                        del self.files[readfile]
            if wait == 1:
                time.sleep(30.1)

    def readline(self, fd):
        returnval = ''
        fileno = fd.fileno()
        fl = fcntl.fcntl(fileno, fcntl.F_GETFL)
        fcntl.fcntl(fileno, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            readval = fd.read(1)
            returnval += readval
            while readval and readval[-1] != '\n':
                readval = fd.read(1)
                returnval += readval
            fcntl.fcntl(fileno, fcntl.F_SETFL, fl)
            return (returnval, True)
        except IOError:
            fcntl.fcntl(fileno, fcntl.F_SETFL, fl)
            return (returnval, False)

    def close(self):
        for readfile in self.files:
            if type(self.files[readfile]) == type(''):
                readfile.close()
            else:
                self.files[readfile][0].poll()
                if not self.files[readfile][0].returncode:
                    self.files[readfile][0].terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Multitail remote and local files.')
    parser.add_argument('logfiles', nargs='+', metavar='FILE',
                        help='Logfiles to follow')
    parser.add_argument('-g', '--grep', action='store', metavar='REGEXP',
                        help='Show only the lines that match the regexp REGEXP')
    params = parser.parse_args()

    grepstring = params.grep or ''

    read_files = {}
    for logfile in params.logfiles:
        if logfile.find(':') >= 0:
            host, logfile = logfile.split(':', 1)
            p = Popen(["ssh", "-o BatchMode=yes", host, "tail", "-f", logfile],
                      stdin=PIPE, stdout=PIPE, close_fds=True)
            read_files[p.stdout] = [p, host + ':' + logfile]
        else:
            fd = open(logfile, 'r')
            read_files[fd] = logfile
    try:
        reader = LineStream(read_files)
        reader.run()
    except KeyboardInterrupt:
        reader.close()

file_dict = {
    open("x"): "x"
}

LineStream(file_dict).run()