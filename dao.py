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
        import datetime
        return Message(id_message=message[0], content=message[1], creation_date=datetime.datetime.fromtimestamp(message[2]),
                       user=DBObject(func=UserDAO.get_user, login=message[3], conn=conn))

    @staticmethod
    @transaction
    def add_message(message, conn=None):
        message.creation_date = datetime.now()
        message.id_message = conn.exec(query="INSERT INTO Message(content, creation_date, user) VALUES"
                                             "(?,?,?)",
                                       params=(message.content, message.creation_date, message.user.login),
                                       opts=InsertOne)
        return message

    @staticmethod
    @transaction
    def get_message(id_message, conn=None):
        message = conn.exec(query="SELECT id_message, content, creation_date, user FROM Message WHERE id_message=?",
                            params=(id_message,), opts=FetchOne)
        if message is None:
            return None
        return MessageDAO._create_message(message, conn)

    @staticmethod
    @transaction
    def create_table(conn=None):
        conn.exec(
            query="CREATE TABLE IF NOT EXISTS Message(id_message INTEGER PRIMARY KEY, content TEXT, "
                  "creation_date TIMESTAMP , user TEXT, FOREIGN KEY (user) REFERENCES User);")


class UserDAO(DAO):
    @staticmethod
    @transaction
    def create_table(conn=None):
        conn.exec(query="CREATE TABLE IF NOT EXISTS User(login TEXT PRIMARY KEY, password TEXT);")

    @staticmethod
    def _create_user(user):
        return User(login=user[0], password=user[1])

    @staticmethod
    def get_user(login, conn=None):
        user = conn.exec(query="SELECT login, password FROM User WHERE login=?", params=(login,),opts=FetchOne)
        if user is None:
            return None
        else:
            return UserDAO._create_user(user=user)

    @staticmethod
    def register(login, password, conn=None):
        conn.begin_transaction(exclusive=True)
        user = conn.exec(query="SELECT login,password FROM User WHERE login=?;", params=(login,), opts=FetchOne)
        if user is None:
            user = UserDAO._create_user(user=(login,password))
            conn.exec("INSERT INTO User(login, password) VALUES (?,?);", params=(login, password), opts=InsertOne)
            conn.commit()
            return user
        else:
            conn.commit()
            return None

    @staticmethod
    @transaction
    def login(login, password, conn=None):
        user = conn.exec("SELECT login, password FROM User WHERE login=? AND password=?;", params=(login, password), opts=FetchOne)
        if user is None:
            return None
        else:
            user = UserDAO._create_user(user=user)
            return user


    @staticmethod
    @transaction
    def get_user(login, conn=None):
        user = conn.exec(query="SELECT login, password FROM User WHERE login=?", params=(login,), opts=FetchOne)
        if user is not None:
            return UserDAO._create_user(user)
        else:
            return None
