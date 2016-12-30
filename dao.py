from abc import ABC, abstractstaticmethod
from datetime import datetime

from DBList import DBObject
from connection import FetchOne, InsertOne, transaction
from dto import User, Message


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


class DAO(ABC):
    @abstractstaticmethod
    def create_table(conn=None):
        pass


class MessageDAO(DAO):
    @staticmethod
    def _create_message(message, conn):
        return Message(id_message=message[0], content=message[1], creation_date=message[2],
                       id_user=DBObject(func=UserDAO.get_user, id_user=message[3], conn=conn))

    @staticmethod
    @transaction
    def add_message(message, conn=None):
        message.creation_date = datetime.now()
        message.id_message = conn.exec(query="INSERT INTO Message(content, creation_date, id_user) VALUES"
                                             "(?,?,?)",
                                       params=(message.content, message.creation_date, message.id_user.id_user),
                                       opts=InsertOne)
        return message

    @staticmethod
    @transaction
    def get_message(id_message, conn=None):
        message = conn.exec(query="SELECT id_message, content, creation_date, id_user FROM Message WHERE id_message=?",
                            params=(id_message,), opts=FetchOne)
        if message is None:
            return None
        return MessageDAO._create_message(message, conn)

    @staticmethod
    @requires_table(table="User")
    @transaction
    def create_table(conn=None):
        conn.exec(
            query="CREATE TABLE IF NOT EXISTS Message(id_message INTEGER PRIMARY KEY, content TEXT, "
                  "creation_date TIMESTAMP , id_user INTEGER, FOREIGN KEY (id_user) REFERENCES User);")


class UserDAO(DAO):
    @staticmethod
    @transaction
    def create_table(conn=None):
        conn.exec(query="CREATE TABLE IF NOT EXISTS User(id_user INTEGER, password TEXT);")

    @staticmethod
    def _create_user(user):
        return User(id_user=user[0], password=user[1])

    @staticmethod
    @transaction
    def add_user(user, conn=None):
        conn.begin_transaction(exclusive=True)  # locks the database to ensure that the number will be unique
        id_user = conn.exec(query="SELECT id_user FROM User WHERE id_user=(SELECT MAX(id_user) FROM User)",
                            opts=FetchOne)  # fetches the last id
        if id_user is None:  # table is empty
            id_user = 1001
        else:  # there is a record
            id_user = id_user[0] + 1  # increases the number
        conn.exec(query="INSERT INTO User(id_user,password) VALUES(?,?)", params=(id_user, user.password))
        user.id_user = id_user
        return user

    @staticmethod
    @transaction
    def get_user(id_user, conn=None):
        user = conn.exec(query="SELECT id_user, password FROM User WHERE id_user=?", params=(id_user,), opts=FetchOne)
        if user is not None:
            return UserDAO._create_user(user)
        else:
            return None
