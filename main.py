import os
import threading, json, dao
import socket
import enum
from dto import Message
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
        return json.dumps({"type": MessageTypes.UNRECOGNIZED_MESSAGE.value})


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


from tornado import websocket


class UserLeaf(User, websocket.WebSocketHandler):

    def send_message(self, message, sender):
        if sender is not self:
            with self.mutex:
                self.write_message(message=message)

    def send_notification(self, notification):
        with self.mutex_observer:
            for observer in self.observers:
                observer.notify(notification=notification)

    def notify(self, notification):
        pass

    def register_observer(self, observer):
        with self.mutex_observer:
            self.observers.append(observer)

    def unregister_observer(self, observer):
        with self.mutex_observer:
            self.observers.remove(observer)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.observers = []
        self.mutex = threading.RLock()
        self.mutex_observer = threading.RLock()
        self.authenticated = False

    def build_message(self, **kwargs):
        return json.dumps(kwargs)

    def _unrecognized_message(self):
        message = MessageParser.unrecognized_message()
        return message

    def _no_login_or_password(self, message):
        if 'login' not in message or 'password' not in message:
            with self.mutex:
                self.write_message(self._unrecognized_message())
                return False
        return True

    def on_message(self, message):
        with self.mutex:
            try:
                message = MessageParser.parse(message=message)
            except InvalidMessage:
                self.write_message(self._unrecognized_message())
            else:
                if self.authenticated is False:
                    if message['type'] == MessageTypes.LOGIN.value:
                        if message['type'] == MessageTypes.LOGIN.value:
                            if self._no_login_or_password(message=message):
                                user = dao.UserDAO.login(login=message['login'], password=message['password'])
                                if user is None:
                                    self.write_message(self.build_message(type=MessageCodes.WRONG_CREDENTIALS.value))
                                else:
                                    self.write_message(self.build_message(type=MessageCodes.LOGGED_IN.value))
                                    self.login = user.login
                                    self.authenticated = True
                                    Socket().add_user(user=user, leaf=self)
                        elif message['type'] == MessageTypes.REGISTER.value:
                            if self._no_login_or_password(message=message):
                                user = dao.UserDAO.register(login=message['login'], password=message['password'])
                                if user is None:
                                    self.write_message(self.build_message(type=MessageCodes.LOGIN_TAKEN.value))
                                else:
                                    self.write_message(self.build_message(type=MessageCodes.USER_REGISTERED.value))
                                    Socket().add_user(user=user, leaf=self)
                else:
                    if message['type'] == MessageTypes.INCOMING_MESSAGE.value:
                        from datetime import datetime
                        from DBList import DBObject
                        message = Message(content=message['message']['content'], creation_date=datetime.now().timestamp(), user=DBObject(func=dao.UserDAO.get_user, login=self.login))
                        message = dao.MessageDAO.add_message(message=message)
                        Socket().send_message(message=json.dumps(obj={
                            "type": MessageTypes.INCOMING_MESSAGE.value,
                            "message": {
                                "user": message.user.login,
                                "creation_date": message.creation_date.timestamp(),
                                "content": message.content,
                                "id_message": message.id_message
                            }
                        }), sender=self)

    def close(self, code=None, reason=None):
        with self.mutex:
            Socket().remove_user(user=self, login=self.login)


class UserComposite(User):
    def __init__(self):
        self._users = []
        self.mutex = threading.RLock()

    def add_user(self, user):
        with self.mutex:
            self._users.append(user)

    def _iterate(self, func):
        with self.mutex:
            for user in self._users:
                func(user=user)

    def remove_user(self, user):
        with self.mutex:
            self._users.remove(user)

    def notify(self, notification):
        self._iterate(func=lambda user: user.notify())

    def register_observer(self, observer):
        self._iterate(func=lambda user: user.register_observer(observer=observer))

    def send_message(self, message, sender):
        self._iterate(func=lambda user: user.send_message(message=message, sender=sender))

    def unregister_observer(self, observer):
        self._iterate(func=lambda user: user.unregister_observer(observer=observer))


class NoUser(Exception):
    pass


SOCKET_BUFF = 4096


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
                item2 = UserComposite()
                item2.add_user(user=item)
                item2.add_user(user=leaf)
                item = item2
            elif isinstance(item, UserComposite):
                item.add_user(user=leaf)
            self._users[user.login] = item
            if leaf in self._dirty:
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

    def send_message(self, message, sender):
        with self.mutex:
            for login, user in self._users.items():
                user.send_message(message=message, sender=sender)


from tornado import web, ioloop


class IndexHandler(web.RequestHandler):
    @web.asynchronous
    def get(self):
        self.render("web/index.html")


if __name__ == "__main__":
    app = web.Application([
        (r'/', IndexHandler),
        (r'/websocket', UserLeaf),
        (r'/static/(.*)', web.StaticFileHandler, {'path': os.path.join(os.getcwd(), 'web/static')})
    ])
    app.listen(port=3000)
    dao.UserDAO.create_table()
    dao.MessageDAO.create_table()
    ioloop.IOLoop.instance().start()
