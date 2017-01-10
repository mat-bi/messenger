import sqlite3
import threading
from abc import ABC, abstractmethod


# A part of an abstract class Connection and its Exceptions/decorators

# superclass of all connection exceptions
class ConnectionException(Exception):
    pass


# superclass of all database exceptions
class DatabaseException(Exception):
    pass


# raised when there is no transaction
class NoTransaction(ConnectionException):
    pass


class OperationNotAvailable(ConnectionException):
    pass


# raised when such a database doesn't exist
class NoDatabase(DatabaseException):
    pass


# raised when invalid savepoint name is provided
class InvalidSavepointName(ConnectionException):
    pass


# a decorator to ensure a valid savepoint name
def incorrect_savepoint_name(func):
    def func_wrapper(self, name, *args, **kwargs):
        import re
        pattern = re.compile(r'^[a-zA-Z]+$')
        if name is not None and pattern.match(name) is None:  # checks if the name contains letters only
            raise InvalidSavepointName()  # if not, raises an exception
        f = func(self, name, *args, **kwargs)
        return f

    return func_wrapper


# a decorator to ensure that if the context is used, the user cannot manually commit, rollbacks and begin transactions
def operation_not_available(func):
    def func_wrapper(self, *args, **kwargs):
        if hasattr(self, '_is_context') and self._is_context is True:  # if used in 'with' clause
            raise OperationNotAvailable()  # raises exception, because it cannot be used in 'with' - the transaction is automatically started and commited/rollbacked
        f = func(self, *args, **kwargs)
        return f

    return func_wrapper


# an abstract class with some generals functions like entering context implemented
class Connection(ABC):
    def __init__(self):
        self._savepoints = []

    @operation_not_available
    @abstractmethod
    def begin_transaction(self):
        pass

    @abstractmethod
    @operation_not_available
    def commit(self):
        pass

    @abstractmethod
    @operation_not_available
    @incorrect_savepoint_name
    def savepoint(self, name):
        pass

    @abstractmethod
    def exec(self, query, params=None, *args, **kwargs):
        pass

    @abstractmethod
    @incorrect_savepoint_name
    def rollback(self, name=None):
        if name is not None:
            if name not in self._savepoints:
                raise InvalidSavepointName()
            else:
                self._savepoints.remove(name)

    def __enter__(self):
        self.begin_transaction()  # begins a new transaction
        self._is_context = True  # a flag to check if in context manager
        return self  # returns itself - a connection to the db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._is_context = False  # sets the flag to false to enable committing
        if exc_type is not None:  # if there was an exception
            self.rollback()  # rollbacks the queries
        else:
            self.commit()  # otherwise commits changes
        ConnectionPool.release_connection(self)  # releases itself to the pool
        return False  # passes the raised exception


class NoExecObject(Exception):
    pass


class ExecCommand(ABC):
    @abstractmethod
    def exec(self, cursor, conn):
        pass


class FetchAll(ExecCommand):
    def exec(self, cursor,conn):
        return cursor.fetchall()


class FetchOne(ExecCommand):
    def exec(self, cursor,conn):
        return cursor.fetchone()


class FetchNone(ExecCommand):
    def exec(self, cursor,conn):
        return None

class InsertOne(ExecCommand):
    def exec(self, cursor,conn):
        return cursor.getconnection().last_insert_rowid()


def no_transaction(func):
    def func_wrapper(self, *args, **kwargs):
        if self._cursor is None:
            raise NoTransaction()
        f = func(self, *args, **kwargs)
        return f

    return func_wrapper

import apsw
class DBConnection(Connection):
    def rollback(self, name=None):
        super(DBConnection, self).rollback(name)
        query = "ROLLBACK"
        if name is not None:  # if savepoint name is provided
            query += " TO {}".format(name)  # adds this name to the query
        query += ";"  # every query must end with a semicolon
        self._cursor.execute(query)  # executes the rollback

    def __init__(self, db='db'):
        super(DBConnection, self).__init__()
        self._db = apsw.Connection(db)
        self._cursor = None
        self.begin_transaction()
        self.exec(query="PRAGMA foreign_keys = ON;")
        self.commit()

    def exec(self, query, params=None, *args, **kwargs):
        if kwargs.get("opts") is None:  # if no option provided
            opts = FetchNone()  # choose to return nothing
        else:
            opts = kwargs.pop("opts")  # otherwise get the provided option
        if isinstance(opts, ExecCommand) is False and issubclass(opts,
                                                                 ExecCommand) is False:  # if the provided option is not an instance of ExecCommand and simultaneously not a subclass of it
            raise NoExecObject()  # raise an exception - if it is not one of the commands, it doesn't make sense to use it
        if params is None:
            self._cursor.execute(query)
        else:
            import datetime
            _params = params
            for idx, param in enumerate(params):
                if isinstance(param, datetime.datetime):
                    _params = _params[0:idx]+(_params[idx].timestamp(),)+_params[idx+1:len(_params)]
            self._cursor.execute(query, _params)
        if isinstance(opts, ExecCommand) is False:  # if the opts provided wasn't an instance, but a class
            opts = opts()  # creates an instance
        return opts.exec(cursor=self._cursor,conn=self._db)  # returns the selected option

    def commit(self):
        super().commit()
        self._cursor.execute("COMMIT")
        self._cursor = None

    def savepoint(self, name):
        super().savepoint(name)
        self._savepoints.append(name)
        self._cursor.execute("SAVEPOINT {};".format(name))

    def begin_transaction(self, exclusive=False):
        super().begin_transaction()
        self._cursor = self._db.cursor()
        if exclusive is False:
            self._cursor.execute("BEGIN TRANSACTION;")
        else:
            self._cursor.execute("BEGIN EXCLUSIVE TRANSACTION;")

    def __del__(self):
        self._db.close()


class ConnectionFactory:
    @staticmethod
    def get_connection(db=None):  # returns an object that represents a database connection
        if db is None:
            return DBConnection()
        else:
            return DBConnection(db=db)


class NotAConnection(Exception):
    pass


def transaction(func, exclusive=False):
    def func_wrapper(*args, **kwargs):
        conn = kwargs.get("conn")
        if conn is None:
            with ConnectionPool.get_connection() as conn:
                kwargs.update(dict(conn=conn))
                f = func(*args, **kwargs)
        else:
            f = func(*args, **kwargs)
        return f

    return func_wrapper


class ConnectionPool:
    _connections = {"available": 32, "connections": []}  # our connection pool with a number of available at the moment
    _cond_var = threading.Condition()  # conditional variable to synchronize threads in a queue

    @staticmethod
    def get_connection():  # returns a connection from the pool
        with ConnectionPool._cond_var:  # gets a mutex
            if ConnectionPool._connections["available"] > 0:  # if any connection is available
                ConnectionPool._connections["available"] -= 1  # decreases the number of available connections
                if len(ConnectionPool._connections[
                           "connections"]) is 0:  # if connections are available, but there isn't any created
                    return ConnectionFactory.get_connection()  # returns a new connection
                else:  # if connection array is not empty
                    return ConnectionPool._connections["connections"].pop()  # returns one of the available
            else:  # no connections available
                while ConnectionPool._connections[
                    "available"] is 0:  # a way to ensure that the thread has any connection available when awoken
                    ConnectionPool._cond_var.wait()  # waits for its turn
                return ConnectionPool._connections["connections"].pop()  # gets any available

    @staticmethod
    def release_connection(conn):
        if isinstance(conn, Connection) is False:  # if the received object is not a connection
            raise NotAConnection()  # raises an exception
        with ConnectionPool._cond_var:  # gets a mutex
            ConnectionPool._connections["available"] += 1  # raises the number of available connections
            ConnectionPool._connections["connections"].append(conn)  # adds the connection to the pool
            ConnectionPool._cond_var.notify()  # wakes any waiting thread up
