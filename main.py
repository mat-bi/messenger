import os
import threading, json, dao
import socket
import enum

import dto
from dto import Message
import threading
from abc import ABC, abstractmethod


class InvalidMessage(Exception):
    pass


class UserState(enum.Enum):
    ACTIVE = 0
    DISCONNECTED = 1


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
        return json.dumps({"type": MessageCodes.UNRECOGNIZED_MESSAGE.value})


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
        with self.mutex:
            self.write_message(notification)

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
                        if self._no_login_or_password(message=message):
                            user = dao.UserDAO.login(login=message['login'], password=message['password'])
                            if user is None:
                                self.write_message(self.build_message(type=MessageCodes.WRONG_CREDENTIALS.value))
                            else:
                                self.login = user.login
                                self.authenticated = True
                                friends = []
                                for friend in user.friends:
                                    friends.append({"login": friend.login, "status": friend.status,
                                                    "state": Socket().get_state(login=friend.login).value})
                                self.write_message(
                                    self.build_message(type=MessageCodes.LOGGED_IN.value, friends=friends))
                                logins = [user.login for user in
                                          dao.FriendDAO.get_users_added_as_friend(user=dto.User(login=self.login))]
                                Socket().add_observer(login=logins, observer=self)
                                Socket().add_user(user=user, leaf=self)

                    elif message['type'] == MessageTypes.REGISTER.value:
                        if self._no_login_or_password(message=message):
                            import connection
                            conn = connection.ConnectionPool.get_connection()
                            user = dao.UserDAO.register(login=message['login'], password=message['password'], conn=conn)
                            connection.ConnectionPool.release_connection(conn)

                            if user is None:
                                self.write_message(self.build_message(type=MessageCodes.LOGIN_TAKEN.value))
                            else:
                                self.write_message(self.build_message(type=MessageCodes.USER_REGISTERED.value))
                                Socket().add_user(user=user, leaf=self)
                else:
                    if message['type'] == MessageTypes.INCOMING_MESSAGE.value:
                        from datetime import datetime
                        from DBList import DBObject
                        message = Message(content=message['message']['content'],
                                          creation_date=datetime.now().timestamp(),
                                          user=DBObject(func=dao.UserDAO.get_user, login=self.login))
                        message = dao.MessageDAO.add_message(message=message)
                        self.write_message(message={
                            "type": MessageCodes.MESSAGE_RECEIVED.value,
                            "id_message": message.id_message
                        })
                        Socket().send_message(message=json.dumps(obj={
                            "type": MessageCodes.INCOMING_MESSAGE.value,
                            "message": {
                                "user": message.user.login,
                                "creation_date": message.creation_date.timestamp(),
                                "content": message.content,
                                "id_message": message.id_message
                            }
                        }), sender=self)
                    elif message['type'] == MessageTypes.CHANGE_STATUS.value:
                        user = dto.User(status=message['status'], login=self.login)
                        dao.UserDAO.change_status(user=user)
                        self.send_notification(
                            notification=json.dumps({"type": MessageCodes.STATUS_CHANGED.value, "user": {
                                "login": self.login,
                                "status": message['status']
                            }}))

                    elif message['type'] == MessageTypes.ADD_FRIEND.value:
                        import connection
                        conn = connection.ConnectionPool.get_connection()
                        if dao.FriendDAO.add_friend(user=dto.User(login=self.login),
                                                    friend=dto.User(login=message['login']), conn=conn):
                            self.write_message(message=json.dumps({
                                "type": MessageCodes.FRIEND_ADDED.value
                            }))
                            Socket().add_observer(login=message['login'], observer=self)
                    elif message['type'] == MessageTypes.REMOVE_FRIEND.value:
                        dao.FriendDAO.remove_friends(user=dto.User(login=self.login),
                                                     friend=dto.User(login=message['login']))
                        Socket().remove_observer(login=message['login'], observer=self)
                    elif message['type'] == MessageTypes.FIND_USERS.value:
                        users = [user.login for user in
                                 dao.UserDAO.find_users(login=message['login'], excluded_login=self.login)]
                        return_message = {}
                        if len(users) is 0:
                            return_message['type'] = MessageCodes.USERS_NOT_FOUND.value
                        else:
                            return_message['type'] = MessageCodes.USERS_FOUND.value
                            return_message['users'] = users
                        self.write_message(json.dumps(return_message))
                    elif message['type'] == MessageTypes.FETCH_FRIENDS.value:
                        friends = [{"login": user.login, "status": user.status, "state": Socket().get_state(user.login).value} for user in dao.FriendDAO.get_friends(user=dto.User(login=self.login))]
                        self.write_message(message=json.dumps({
                            "type": MessageCodes.FRIENDS_FETCHED.value,
                            "friends": friends
                        }))
                    elif message['type'] == MessageTypes.LOGGED_USER.value:
                        user = dao.UserDAO.get_user(login=self.login)
                        self.write_message(message=json.dumps({
                            "type": MessageCodes.LOGGED_USER.value,
                            "user": {
                                "login": user.login,
                                "status": user.status
                            }
                        }))
                    elif message['type'] == MessageTypes.LOGOUT.value:
                        del self.login
                        self.authenticated = False
                        self.write_message(message=json.dumps({
                            "type": MessageCodes.LOGGED_OUT.value
                        }))


    def on_close(self, code=None, reason=None):
        with self.mutex:
            with self.mutex_observer:
                for observer in self.observers:
                    observer.unregister_observer(observer=self)
            if self.authenticated is True:
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
            if len(self._users) is 0:
                return None
            else:
                return self

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
    CHANGE_STATUS = 4
    ADD_FRIEND = 5
    REMOVE_FRIEND = 6
    FIND_USERS = 7
    FETCH_FRIENDS = 8
    LOGGED_USER = 9
    LOGOUT = 100


class MessageCodes(enum.Enum):
    UNRECOGNIZED_MESSAGE = 0
    SEND_CREDENTIALS = 1
    WRONG_CREDENTIALS = 2
    LOGGED_IN = 3
    LOGIN_TAKEN = 4
    USER_REGISTERED = 5
    STATUS_CHANGED = 6
    FRIEND_ADDED = 7
    STATE_CHANGED = 8
    USERS_FOUND = 9
    USERS_NOT_FOUND = 10
    MESSAGE_RECEIVED = 11
    INCOMING_MESSAGE = 12
    FRIENDS_FETCHED = 13
    LOGGED_USER = 14
    LOGGED_OUT = 100


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

    def get_state(self, login):
        with self.mutex:
            user = self._users.get(login)
            if user is None:
                return UserState.DISCONNECTED
            else:
                return UserState.ACTIVE

    def remove_observer(self, login, observer):
        with self.mutex:
            self._users.get(login).remove_observer(observer=observer)

    def _add_observer(self, login, observer):
        user = self._users.get(login)
        if user is not None:
            observer.register_observer(observer=user)

    def add_observer(self, login, observer):
        with self.mutex:
            if isinstance(login, list) or isinstance(login, tuple):
                for item in login:
                    self._add_observer(login=item, observer=observer)
            else:
                self._add_observer(login=login, observer=observer)

    def add_user(self, user, leaf):
        with self.mutex:
            item = self._users.get(user.login)
            if item is None:
                item = leaf
                leaf.send_notification(notification=json.dumps({
                    "type": MessageCodes.STATE_CHANGED.value,
                    "state": UserState.ACTIVE.value,
                    "login": user.login
                }))
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
                user.send_notification(notification=json.dumps({
                    "type": MessageCodes.STATE_CHANGED.value,
                    "state": UserState.DISCONNECTED.value,
                    "login": user.login
                }))
                if item.remove_user(user=user) is None:
                    self._users.pop(login)

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
        (r'/(.*)', web.StaticFileHandler, {'path': os.path.join(os.getcwd(), 'web')})
    ])
    app.listen(port=3000)
    dao.UserDAO.create_table()
    dao.MessageDAO.create_table()
    dao.FriendDAO.create_table()
    ioloop.IOLoop.instance().start()
