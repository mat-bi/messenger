import threading, json, dao
import socket
import enum

import threading
from abc import ABC, abstractmethod

class InvalidMessage(Exception):
    pass

class MessageParser:
    @staticmethod
    def parse(message):
        try:
            message = json.loads(s=message, encoding='utf-8')
        except ValueError:
            raise InvalidMessage()
        else:
            if 'type' not in message:
                raise InvalidMessage()
            return message

    @staticmethod
    def unrecognized_message():
        return "{}\r\n".format(json.dumps({"type": MessageTypes.UNRECOGNIZED_MESSAGE.value})).encode("utf-8")


class User(ABC):
    @abstractmethod
    def send_message(self, message, conn):
        pass

    @abstractmethod
    def notify(self, notification):
        pass

    @abstractmethod
    def register_observer(self, observer):
        pass

    @abstractmethod
    def unregister_observer(self, observer):
        pass


class UserLeaf(User, threading.Thread):
    def _iterate(self, func):
        for observer in self.observers:
            func(observer=observer)

    def send_message(self, message,conn):
        with self.mutex:
            self.conn.send(message)

    def send_notification(self, notification):
        for observer in self.observers:
            observer.notify(notification=notification)

    def notify(self, notification):
        pass

    def register_observer(self, observer):
        self.observers.append(observer)

    def unregister_observer(self, observer):
        self.observers.remove(observer)

    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.observers = []
        self.mutex = threading.RLock()
    def build_message(self, **kwargs):
        return "{}\r\n".format(json.dumps(kwargs)).encode("utf-8")

    def _unrecognized_message(self, conn):
        message = MessageParser.unrecognized_message()
        conn.send(message)

    def _no_login_or_password(self, message, conn):
        if 'login' not in message or 'password' not in message:
            self._unrecognized_message(conn=conn)
            return False
        return True
    def run(self):
        with self.conn:
            conn, addr = self.conn, self.addr
            while True:  # waiting for the first message
                data = conn.recv(SOCKET_BUFF)  # receiving json object
                if not data:  # no data - connection is closed
                    return
                try:
                    data = MessageParser.parse(message=data.decode("utf-8"))
                except InvalidMessage:
                    self._unrecognized_message(conn=conn)
                else:
                    a = MessageTypes.LOGIN == 0
                    if data['type'] == MessageTypes.LOGIN.value:
                        if self._no_login_or_password(message=data, conn=conn):
                            user = dao.UserDAO.login(login=data['login'], password=data['password'])
                            if user is None:
                                conn.send(self.build_message(message=MessageCodes.WRONG_CREDENTIALS.value))
                            else:
                                conn.send(self.build_message(message=MessageCodes.LOGGED_IN.value))
                                self.login = user.login
                                Socket().add_user(user=user, conn=conn, addr=addr)
                                break
                    elif data['type'] == MessageTypes.REGISTER.value:
                        if self._no_login_or_password(message=data, conn=conn):
                            user = dao.UserDAO.register(login=data['login'], password=data['password'])
                            if user is None:
                                conn.send(self.build_message(message=MessageCodes.LOGIN_TAKEN.value))
                            else:
                                conn.send(self.build_message(message=MessageCodes.USER_REGISTERED.value))
                                Socket().add_user(user=user, conn=conn, addr=addr)
                                break
            while True:
                data = self.conn.recv(SOCKET_BUFF).decode("utf-8")
                with self.mutex:
                    if not data:
                        break
                    try:
                        data = MessageParser.parse(message=data)
                    except ValueError:
                        self.conn.send(MessageParser.unrecognized_message())
                    else:
                        if data['type'] == MessageTypes.INCOMING_MESSAGE:
                            pass

            Socket().remove_user(user=self, login=self.login)


class UserComposite(User):
    def __init__(self):
        self._users = []

    def add_user(self, user):
        self._users.append(user)

    def _iterate(self, func):
        for user in self._users:
            func(user=user)

    def notify(self, notification):
        self._iterate(func=lambda user: user.notify())

    def register_observer(self, observer):
        self._iterate(func=lambda user: user.register_observer(observer=observer))

    def send_message(self, message, conn):
        self._iterate(func=lambda user: user.send_message(message=message, conn=conn))

    def unregister_observer(self, observer):
        self._iterate(func=lambda user: user.unregister_observer(observer=observer))


class NoUser(Exception):
    pass


SOCKET_BUFF = 1024


class MessageTypes(enum.Enum):
    LOGIN = 0
    REGISTER = 1
    INCOMING_MESSAGE = 2
    UNRECOGNIZED_MESSAGE = 3


class MessageCodes(enum.Enum):
    SEND_CREDENTIALS = 1
    WRONG_CREDENTIALS = 2
    LOGGED_IN = 3
    LOGIN_TAKEN = 4
    USER_REGISTERED = 5


def singleton(cls):
    instances = {}

    def getinstance():
        with cls.mutex:
            if cls not in instances:
                instances[cls] = cls()
            return instances[cls]

    return getinstance


@singleton
class Socket(object):
    mutex = threading.RLock()

    def __init__(self):
        self._users = dict()
        self._dirty = []

    def add_user(self, user, leaf):
        with self.mutex:
            item = self._users.get(user.login)
            if item is None:
                item = leaf
            elif isinstance(item, UserLeaf):
                item = UserComposite()
                item.add_user(user=leaf)
            elif isinstance(item, UserComposite):
                item.add_user(user=leaf)
            self._users[user.login] = item
            self._dirty.remove(leaf)

    def remove_user(self, user, login):
        with self.mutex:
            if self._users.get(login) is None:
                raise NoUser()
            item = self._users[login]
            if isinstance(item, UserLeaf):
                del self._users[login]
            elif isinstance(item, UserComposite):
                self._users[login] = item.remove_user(user=user)

    def send_message(self, message, conn):
        with self.mutex:
            for user in self._users:
                user.send_message(message=message, conn=conn)



    def handle(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
        s.bind(('', 3000))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            with self.mutex:
                leaf = UserLeaf(conn=conn, addr=addr)
                self._dirty.append(leaf)
                leaf.start()



if __name__ == "__main__":
    dao.UserDAO.create_table()
    dao.MessageDAO.create_table()
    Socket().handle()
