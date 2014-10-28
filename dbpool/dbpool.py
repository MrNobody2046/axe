import functools
import threading
import Queue
import warnings
import MySQLdb


MAX_CONNECTIONS = 100


class BaseHandler(object):
    """

    """
    def __init__(self, conn_name, conn):
        self._name = conn_name
        self._conn = conn
        self._cursor = conn.cursor()
        self.initialize()

    def initialize(self):
        pass

    def show_tables(self):
        return '\n'.join([','.join(i) for i in self.fetch_data("show tables")])

    def close(self):
        """
        not close really , release the connection
        :return:
        """
        del self._conn, self._cursor

    def fetch_data(self, *args, **kwargs):
        """
        query and get result
        :param args:
        :param kwargs:
        :return: list contain each row as a tuple(dict if use DictCursor)
        """
        self._cursor.execute(*args, **kwargs)
        res = self._cursor.fetchall()
        self._conn.rollback()
        return res

    def execute(self, *args, **kwargs):
        """
        execute sql and auto commit it.
        :param kwargs:
        :return:
        """
        auto_commit = kwargs.pop("auto_commit", True)
        self._cursor.execute(*args, **kwargs)
        if auto_commit:
            return self.commit()

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()


class ConnectionPoolOverLoadError(Exception):
    pass


class ConnectionNotInPoolError(Exception):
    pass


class ConnectionNameConflictError(Exception):
    pass


class AlreadyConnectedError(Exception):
    pass


class ClassAttrNameConflictError(Exception):
    pass


class ConnectionNotFoundError(Exception):
    pass


class ConnectionPool(object):
    """
    ConnectionPool holds the certain amount of connections in queue,
    and use connect get the live connection from queue,once the you
     need not use it,you should release it explicitly.
    This class actually work with DataBaseConnector
    """
    MAX_CONNECTIONS = MAX_CONNECTIONS

    def __init__(self, name, **connection_kwargs):
        self.name = name
        self.connection_kwargs = connection_kwargs
        self.queue = Queue.Queue(self.MAX_CONNECTIONS)
        self._lock = threading.Lock()
        self._live_connection_count = 0
        self._peak_connection_count = 0
        self._open_connections = []

    def __repr__(self):
        return "<%s : '%s'>" % (self.__class__.__name__, self.name)

    @property
    def live_connections(self):
        return self._live_connection_count

    def connect(self):
        return self._connect()

    def pop_open_connection(self, conn):
        with self._lock:
            try:
                self._open_connections.remove(conn)
            except Exception:
                raise ConnectionNotInPoolError("Connection seems not belong to %s" % self.__repr__())

    def _connect(self):
        """
        open the new connection if connection pool is not overflow
        :return:
        """
        with self._lock:
            if self.queue.empty():
                if self.MAX_CONNECTIONS <= 0 or self.live_connections < self.MAX_CONNECTIONS:
                    conn = MySQLdb.connect(**self.connection_kwargs)
                else:
                    raise ConnectionPoolOverLoadError(
                        "Connections of %s reach the %d limit" % (self.__repr__(), self.MAX_CONNECTIONS))
            else:
                conn = self.queue.get()
            self._open_connections.append(conn)
            self._live_connection_count = len(self._open_connections)
            if self._live_connection_count > self._peak_connection_count:
                self._peak_connection_count = self._live_connection_count
            return conn

    def release(self, conn):
        self.pop_open_connection(conn)
        with self._lock:
            try:
                conn.rollback()
            except MySQLdb.OperationalError:
                print("connection seems closed, drop it.")
            else:
                self.queue.put(conn)
            finally:
                self._live_connection_count -= 1

    def close(self, force=True):
        with self._lock:
            conns = [c for c in self._open_connections]
            conns.extend([self.queue.get() for _ in xrange(self.queue.qsize()) if self.queue.not_empty])
            for c in conns:
                try:
                    c.close()
                except Exception, e:
                    if force:
                        print("Force closed error: %r" % e)
                    else:
                        raise e


def get_class_attrs(cls):
    return [attr for attr in dir(cls) if not attr.startswith('_')]


class DataBaseConnector(object):
    """
    DataBaseConnector provide high-level handler of each
     connection pool .
     the handler are thread-safe, like connection pool
      you can connect and release it.
    """

    _instance_lock = threading.Lock()
    default_db = None

    def __init__(self, connection_handler=None, delegate=False):
        """
        Global DataBaseConnector with specific connection handler,
        call DataBaseConnector.connect to passing the mysql connection to this handler
        and use DataBaseConnector.db access
        current database connection wrapper class.
        :param connection_handler:
        :return:
        """
        self._root_connection_handler = connection_handler
        self._connection_pools = {}
        # the queue stores available handler instance
        with DataBaseConnector._instance_lock:
            DataBaseConnector._instance = self
        self._delegate = None
        self._lock = threading.Lock()
        self._current = threading.local()
        self._current._connection_handler = connection_handler
        self.set_delegate(delegate)

    def __getattr__(self, attr):
        if not self._delegate or (attr.startswith('_') or not hasattr(self.handler, attr)):
            return self.__getattribute__(attr)
        else:
            return getattr(self.handler, attr)

    @staticmethod
    def initialized():
        """Returns true if the singleton instance has been created."""
        return hasattr(DataBaseConnector, "_instance")

    @staticmethod
    def instance():
        if not hasattr(DataBaseConnector, "_instance"):
            with DataBaseConnector._instance_lock:
                if not hasattr(DataBaseConnector, "_instance"):
                    DataBaseConnector._instance = DataBaseConnector()
        return DataBaseConnector._instance

    @property
    def conn(self):
        return self._connection_stack[-1]._conn

    @property
    def handler(self):
        return self._connection_stack[-1]

    @property
    def _connection_handler(self):
        try:
            return self._current._connection_handler
        except:
            warnings.warn("not specified connection handler in current thread, use root connect handler", RuntimeWarning)
            return self._root_connection_handler

    @property
    def _connection_stack(self):
        if not hasattr(self._current, "connection_stack"):
            self._current.connection_stack = []
        return self._current.connection_stack

    def set_delegate(self, delegate):
        """
        if open delegate(default is opened), the DataBaseConnector instance
        will share api with its current handler, that means it works like
        the connection handler instance.
        :param delegate: bool
        :return:None
        """
        if delegate:
            if set(get_class_attrs(self._connection_handler)).intersection(set(get_class_attrs(self))):
                raise ClassAttrNameConflictError(
                    "if open delegate,ConnectionHandler's attr name should not appear in DataBaseConnector")
            self._delegate = True
        else:
            self._delegate = False

    def load_database_cfg(self):
        pass

    def add_database(self, database, **kwargs):
        """
        :param database: string database name
        :param kwargs: connection kwargs
        :return:
        """
        override = kwargs.pop("override", False)
        ignore = kwargs.pop("ignore", False)
        conns = ConnectionPool(database, **kwargs)  # noticed connection pool not establish connection if not used
        if self._connection_pools.has_key(database):
            if ignore:
                # ignore if exist connections
                return
            if not override:
                msg = "already exist connection '%s',override or rename it." % database
                raise ConnectionNameConflictError(msg)
            else:
                self._connection_pools[database].close()
                # should close override connection first
        else:
            if not self._connection_pools and not self.default_db:
                self.default_db = database
                # set the first connection as default db connection
        self._connection_pools[database] = conns

    def get_database(self, dbname):
        return self._connection_pools.get(dbname)

    def add_databases(self, **kwargs):
        """
        :param kwargs: use database name as key , connection kwargs dict as value
        :return:
        """

    def connect(self, conn_name):
        """
        Mapping current connection handler's method to DataBaseConnector
        :return:
        """
        _conn = self._connection_pools[conn_name].connect()
        handler = self._connection_handler(conn_name, _conn)
        self._connection_stack.append(handler)

    def _push(self, conn):
        self._current.connection_stack.append(conn)

    def _pop(self):
        self._current.connection_stack.pop()

    def release(self):
        """
        :return:
        """
        handler = self._connection_stack.pop()
        self._connection_pools[handler._name].release(handler._conn)
        handler.close()
        del handler


dbc_instance = DataBaseConnector(BaseHandler, delegate=True)


def with_db(db=None, lazy_load=True):
    """
    :param db:database connection name
    :return:the decorator with specific db connection
    """
    if not lazy_load:
        if not db:
            db = dbc_instance.default_db
        if not dbc_instance._connection_pools.has_key(db):
            raise ConnectionNotFoundError("Not found connection for '%s', use dbc.add_database add the connection" % db)

    def _with_db(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            dbc_instance.connect(db)
            try:
                return func(*args, **kwargs)
            finally:
                dbc_instance.release()

        return _wrapper

    return _with_db


def get_db_decorator(handler=BaseHandler, **connection_kwargs):
    """
    :return the decorator and not use global DataBaseConnector
    :param handler:
    :param connection_kwargs:
    :return:
    """
    dbc = DataBaseConnector(handler, delegate=True)
    dbc.add_database("conn", **connection_kwargs)

    def _with_db(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            dbc.connect("conn")
            res = func(*args, **kwargs)
            dbc.release()
            return res

        return _wrapper

    return _with_db


if __name__ == "__main__":
    dbc_instance.add_database("rdb", host="127.0.0.1",
                              port=3306,
                              user="root",
                              passwd="zxc",
                              db="test",
                              charset="utf8",
                              use_unicode=True)
    import time, random

    def test():
        @with_db(db='rdb')
        def _test():
            dbc_instance.handler.show_tables()

        ras = random.random()
        time.sleep(ras)
        _test()

    ths_test = [threading.Thread(target=test).start() for i in range(1000)]
    time.sleep(1)
    connection_pool = dbc_instance.get_database("rdb")
    # connection_pool.close()
    print "Queue size:", connection_pool.queue.qsize(), "Peak conns:", connection_pool._peak_connection_count
    print connection_pool._open_connections
