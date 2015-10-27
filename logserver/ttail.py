#!/usr/bin/env python
import time
import sys
from subprocess import Popen,PIPE
import fcntl
import select
import os
import Queue


class FReader(object):
    """
    """
    NORMAL = 1
    SSH = 2

    def __init__(self, path):
        """
        :param path:
        :return:
        """
        self.path = path
        self.abs_path = os.path.abspath(path)
        {True: self.connect_remote_file, False: self.connect_local_file}[path.find(":") != -1](path)
        self._buffer = ""
        self.queue = Queue.Queue()
        self.line = []

    def connect_remote_file(self, path):
        host, remote_file = path.split(':', 1)
        self.basename = os.path.basename(remote_file)
        self.fd = Popen(["ssh", "-o BatchMode=yes", host, "tail", "-f", remote_file],
                        stdin=PIPE, stdout=PIPE, close_fds=True)
        self._t = self.SSH

    def connect_local_file(self, path):
        self._t = self.NORMAL
        self.fd = open(path)
        self.basename = os.path.basename(path)

    @property
    def file_name(self):
        return self.basename

    def __hash__(self):
        return self.fd.__hash__()

    def read_line(self):
        self._buffer = ""
        fd = self.fd.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            self._buffer += self.fd.read(1)
            while self._buffer[-1] != '\n':
                self._buffer += self.fd.read(1)
            return True
        except IOError:
            return False
        finally:
            fcntl.fcntl(fd, fcntl.F_SETFL, fl)

    def read(self):
        if self.is_ssh_file:
            self.fd.poll()
        if self.read_line():
            return self._buffer
        else:
            return ""

    @property
    def is_ssh_file(self):
        return self._t == self.SSH

class CH(object):
    def __init__(self, m):
        self.m = m

    def __hash__(self):
        return 1


class Tail(object):
    def __init__(self):
        self.fd2freader_dict = {}
        self._fd_list = []

    def add_freader(self, freader):
        assert isinstance(freader, FReader)
        self.fd2freader_dict[freader.fd] = freader
        self._fd_list.append(freader.fd)

    def run(self):
        print "Start", self._fd_list
        while len(self.fd2freader_dict) > 0:
            rlist, _, _ = select.select(self._fd_list, [], [],1)
            for read_file in rlist:
                freader = self.fd2freader_dict[read_file]
                buf = freader.read()
                if buf:
                    sys.stdout.write(buf)
            # print rlist


# t = Tail()
# t.add_freader(FReader("./x"))
# t.run()
#
# 1 / 0


class LineStream(object):
    def __init__(self, file_dict):
        self.files = file_dict
        self.file_list = file_dict.keys()

    def run(self):
        buffers = {}
        while len(self.file_list) > 0:
            print "loop"
            rlist, _, _ = select.select(self.file_list, [], [])
            print rlist, _, _
            wait = 0
            for readfile in rlist:
                fd = readfile
                if isinstance(fd, basestring):
                    newline, full = self.readline(fd)
                    if fd in buffers:
                        buffers[fd] += newline
                    else:
                        buffers[fd] = newline
                    if buffers[fd] and full:
                        print "%s::%s" % (self.files[fd],
                                          buffers[fd]),
                        del buffers[fd]
                    elif not buffers[fd] and wait == 0:
                        wait = 1
                else:
                    # for ssh pipes
                    wait = 2
                    # pipe = self.files[fd][0]
                    # pipe.poll()
                    # newline, full = self.readline(readfile)
                    # if readfile in buffers:
                    #     buffers[readfile] += newline
                    # else:
                    #     buffers[readfile] = newline
                    # if buffers[readfile] and full:
                    #     print "%s::%s" % (self.files[readfile][1],
                    #                       buffers[readfile]),
                    #     del buffers[readfile]
                    # if pipe.returncode:
                    #     del self.files[readfile]
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
    # parser = argparse.ArgumentParser(
    #     description='Multitail remote and local files.')
    # parser.add_argument('logfiles', nargs='+', metavar='FILE',
    #                     help='Logfiles to follow')
    # parser.add_argument('-g', '--grep', action='store', metavar='REGEXP',
    #                     help='Show only the lines that match the regexp REGEXP')
    # params = parser.parse_args()
    #
    # grepstring = params.grep or ''
    #
    # read_files = {}
    # for logfile in params.logfiles:
    #     if logfile.find(':') >= 0:
    #         host, logfile = logfile.split(':', 1)
    #         p = Popen(["ssh", "-o BatchMode=yes", host, "tail", "-f", logfile],
    #                   stdin=PIPE, stdout=PIPE, close_fds=True)
    #         read_files[p.stdout] = [p, host + ':' + logfile]
    #     else:
    #         fd = open(logfile, 'r')
    #         read_files[fd] = logfile
    # try:
    #     reader = LineStream(read_files)
    #     reader.run()
    # except KeyboardInterrupt:
    #     reader.close()

    file_dict = {
        open("x"): "x"
    }

    LineStream(file_dict).run()
