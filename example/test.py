from dbpool import dbc_instance, with_db
import threading
import time, random


if __name__ == "__main__":
    dbc_instance.add_database("rdb", host="127.0.0.1",
                              port=3306,
                              user="root",
                              passwd="zxc",
                              db="test",
                              charset="utf8",
                              use_unicode=True)

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