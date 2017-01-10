from abc import ABC, abstractstaticmethod
from datetime import datetime

from DBList import DBObject, DBList
from connection import FetchOne, InsertOne, transaction, FetchNone, FetchAll
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

def return_users(func):
    def func_wrapper(*args, **kwargs):
        users = func(*args, **kwargs)
        return_value = []
        for user in users:
            return_value.append(UserDAO._create_user(user=user))
        return return_value
    return func_wrapper


class FriendDAO(DAO):

    @staticmethod
    @transaction
    def create_table(conn=None):
        conn.exec(query="CREATE TABLE IF NOT EXISTS Friend(friend1 TEXT, friend2 TEXT, FOREIGN KEY (friend1) REFERENCES User(login), FOREIGN KEY (friend2) REFERENCES User(login), PRIMARY KEY (friend1, friend2))")


    @staticmethod
    def add_friend(user, friend, conn=None):
        conn.begin_transaction(exclusive=True)
        row = conn.exec(query="SELECT friend1,friend2 FROM FRIEND WHERE friend1=? AND friend2=?", params=(user.login, friend.login), opts=FetchOne)
        if row is None:
            conn.exec(query="INSERT INTO Friend(friend1, friend2) VALUES(?,?)", params=(user.login, friend.login))
            conn.commit()
            return True
        conn.commit()
        return False

    @staticmethod
    @return_users
    @transaction
    def get_users_added_as_friend(user, conn=None):
        return conn.exec(query="SELECT U.login, U.password, U.status FROM Friend F JOIN User U ON U.login=f.friend1 WHERE F.friend2=?", params=(user.login,), opts=FetchAll)


    @staticmethod
    @return_users
    @transaction
    def get_friends(user, conn=None):
        return conn.exec(
            query="SELECT U.login, U.password, U.status FROM FRIEND F JOIN User U ON U.login=F.friend1 WHERE F.friend2=? ",
            params=(user.login, user.login), opts=FetchAll)


    @staticmethod
    def remove_friends(user, friend, conn=None):
        conn.exec(query="DELETE FROM Friend WHERE friend1=? AND friend2=?", params=(user.login, friend.login))

class UserDAO(DAO):
    @staticmethod
    @transaction
    def create_table(conn=None):
        conn.exec(query="CREATE TABLE IF NOT EXISTS User(login TEXT PRIMARY KEY, password TEXT, status TEXT);")

    @staticmethod
    def _create_user(user):
        return User(login=user[0], password=user[1], status=user[2], friends=DBList(func=FriendDAO.get_friends, user=User(login=user[0])))

    @staticmethod
    @transaction
    def get_status(user, conn=None):
        status = conn.exec(query="SELECT status FROM USER WHERE login=?", params=(user.login), opts=FetchOne)
        if status is None:
            return ""
        else:
            return status[0]

    @staticmethod
    @transaction
    def change_status(user,conn=None):
        conn.exec(query="UPDATE User SET status=? WHERE login=?", params=(user.status, user.login), opts=FetchNone)

    @staticmethod
    @transaction
    def get_user(login, conn=None):
        user = conn.exec(query="SELECT login, password, status FROM User WHERE login=?", params=(login,),opts=FetchOne)
        if user is None:
            return None
        else:
            return UserDAO._create_user(user=user)

    @staticmethod
    def register(login, password, conn=None):
        conn.begin_transaction(exclusive=True)
        user = conn.exec(query="SELECT login,password, status FROM User WHERE login=?;", params=(login,), opts=FetchOne)
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
        user = conn.exec("SELECT login, password, status FROM User WHERE login=? AND password=?;", params=(login, password), opts=FetchOne)
        if user is None:
            return None
        else:
            user = UserDAO._create_user(user=user)
            return user

    @staticmethod
    @return_users
    @transaction
    def find_users(login, excluded_login='', conn=None):
        return conn.exec(query="SELECT login, password, status FROM User WHERE login LIKE (?|| '%') AND LOGIN != ?", params=(login, excluded_login), opts=FetchAll)


    '''@staticmethod
    @transaction
    def get_user(login, conn=None):
        user = conn.exec(query="SELECT login, password FROM User WHERE login=?", params=(login,), opts=FetchOne)
        if user is not None:
            return UserDAO._create_user(user)
        else:
            return None'''
