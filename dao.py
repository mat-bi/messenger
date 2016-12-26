from connection import FetchOne, ConnectionPool, FetchAll, InsertOne, transaction
from dto import User


class NoDAOTable(Exception):
    pass


def requires_table(table):
    def requires_table_decorator(func):
        def func_wrapper(conn, *args, **kwargs):
            try:
                globals()["{}DAO".format(table)].create_table(conn=conn)
            except KeyError:
                raise NoDAOTable()
            return func(conn=conn, *args, **kwargs)

        return func_wrapper

    return requires_table_decorator


class MessageDAO:
    @staticmethod
    @transaction
    def add_message(message, conn=None):
        message.id_message = conn.exec(query="INSERT INTO Message(content, id_user_to, id_user_from, unread) VALUES"
                                             "(?,?,?,?)",
                                       params=(message.content, message.id_user_to, message.id_user_from,
                                               message.unread), opts=InsertOne)
        return message

    @staticmethod
    @transaction
    def get_unread_messages(id_user_to, conn=None):
        conn.exec("BEGIN EXCLUSIVE;")
        messages = conn.exec(query="SELECT * FROM Message WHERE id_user_to=? AND unread=?", params=(id_user_to, True),
                             opts=FetchAll)
        conn.exec(query="UPDATE Message SET unread=? WHERE id_user_to=?", params=(False, id_user_to))
        return messages

    @staticmethod
    @transaction
    def get_message(id_message, conn=None):
        message = conn.exec(query="SELECT * FROM Message WHERE id_message=?", params=(id_message,), opts=FetchOne)
        return message

    @staticmethod
    @requires_table(table="User")
    @transaction
    def create_table(conn=None):
        conn.exec(
            query="CREATE TABLE IF NOT EXISTS Message(id_message INTEGER PRIMARY KEY, content TEXT, "
                  "id_user_to INTEGER, id_user_from INTEGER,unread BOOLEAN);")


class UserDAO:
    @staticmethod
    @transaction
    def create_table(conn=None):
        conn.exec(query="CREATE TABLE IF NOT EXISTS User(id_user INTEGER, password TEXT);")

    @staticmethod
    @transaction
    def add_user(password, conn=None):
        conn.exec(query="BEGIN EXCLUDE")  # locks the database to ensure that the number will be unique
        user = conn.exec(query="SELECT id_user FROM User WHERE id_user=(SELECT MAX(id_user) FROM User)",
                         opts=FetchOne)  # fetches the last id
        if user is None:  # table is empty
            id_user = 1001
        else:  # there is a record
            id_user = user[0] + 1  # increases the number
        conn.exec(query="INSERT INTO User(id_user,password) VALUES(?,?)", params=(id_user, password))
        return User(id_user=id_user)

    @staticmethod
    @transaction
    def get_user(id_user, conn=None):
        user = conn.exec(query="SELECT * FROM User WHERE id_user=?", params=(id_user,), opts=FetchOne)
        if user is not None:
            return User(id_user=id_user)
        else:
            return None
