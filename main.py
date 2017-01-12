import os
import threading, json, dao
import socket
import enum

import sys

import dto
from dto import Message
import threading
from abc import ABC, abstractmethod


class MessageTypes(enum.Enum):
    LOGIN = 0
    REGISTER = 1
    INCOMING_MESSAGE = 2
    # UNRECOGNIZED_MESSAGE = 3
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
    FRIEND_DOESNT_EXIST = 15
    FRIENDSHIP_EXISTS = 16
    CANNOT_ADD_ITSELF = 17
    ACCESS_RESTRICTED = 50
    LOGGED_OUT = 100


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


class Controller(ABC):
    def __init__(self, login, context):
        self._login = login
        self._context = context

    @property
    def login(self):
        return self._login

    @property
    def context(self):
        return self._context


class LoginObject:
    def __init__(self, login=None, content=None):
        self._content = content
        if login is not None:
            self._login = login
            self._logged = True
        else:
            self._logged = False
            self._login = None

    def log_in(self, login):
        self.login = login
        self._logged = True

    @property
    def content(self):
        return self._content

    @property
    def logged(self):
        return self._logged

    @property
    def login(self):
        return self._login

    @login.setter
    def login(self, value):
        self._login = value

    def log_out(self):
        self._login = None
        self._logged = False


class ReturnView:
    def __init__(self, **kwargs):
        self.fields = kwargs
        self.__dict__.update(kwargs)


class AccessRestricted(Exception):
    pass


def logged(func):
    def func_wrapper(self, *args, **kwargs):
        if self.login.logged is True:
            f = func(self, *args, **kwargs)
        else:
            raise AccessRestricted()
        return f

    return func_wrapper


def unlogged(func):
    def func_wrapper(self, *args, **kwargs):
        if self.login.logged is False:
            f = func(self, *args, **kwargs)
        else:
            raise AccessRestricted()
        return f

    return func_wrapper


class LoggedInController(Controller):
    @unlogged
    def action(self, login, password):
        user = dao.UserDAO.login(login=login, password=password)  # tries to get the user from the database
        if user is None:  # no such a user
            return ReturnView(type=MessageCodes.WRONG_CREDENTIALS)  # it means that the credentials are wrong
        else:  # DB returned a row
            friends = [{"login": friend.login, "status": friend.status,
                        "state": Socket().get_state(login=friend.login).value} for friend in
                       user.friends]  # gets all friends of the current user
            logins = [user.login for user in
                      dao.FriendDAO.get_users_added_as_friend(user=dto.User(
                          login=login))]  # gets all the users that added the current user as a friend
            Socket().add_observer(login=logins,
                                  observer=self.context)  # the socket object has the list of current connected users, we use it to connect the objects in the observator pattern
            self.login.log_in(login=login)
            Socket().add_user(user=user, leaf=self.context)
            return ReturnView(type=MessageCodes.LOGGED_IN,
                              friends=friends)  # writes a message to the client, to inform it that the log-in was successful


class RegisterController(Controller):
    @unlogged
    def action(self, login, password):
        import connection
        conn = connection.ConnectionPool.get_connection()
        user = dao.UserDAO.register(login=login, password=password, conn=conn)
        connection.ConnectionPool.release_connection(conn)

        if user is None:  # a user with the provided login exists
            return ReturnView(type=MessageCodes.LOGIN_TAKEN)
        else:  # no user with the provided login, the registration was successful, so we can log the user in
            self.login.log_in(login=login)
            Socket().add_user(user=user, leaf=self.context)
            return ReturnView(type=MessageCodes.USER_REGISTERED)


class IncomingMessageController(Controller):
    @logged
    def action(self, content):
        from datetime import datetime
        from DBList import DBObject
        message = Message(content=content,
                          creation_date=datetime.now().timestamp(),
                          user=DBObject(func=dao.UserDAO.get_user, login=self.login.login))
        message = dao.MessageDAO.add_message(message=message)
        Socket().send_message(ReturnView(type=MessageCodes.INCOMING_MESSAGE,
                                         message={
                                             "user": message.user.login,
                                             "creation_date": message.creation_date.timestamp(),
                                             "content": message.content,
                                             "id_message": message.id_message
                                         }
                                         ), sender=self.context)
        return ReturnView(type=MessageCodes.MESSAGE_RECEIVED,
                          id_message=message.id_message)


class ChangeStatusController(Controller):
    @logged
    def action(self, status):
        user = dto.User(status=status, login=self.login.login)
        dao.UserDAO.change_status(user=user)
        self.context.send_notification(
            notification=ReturnView(type=MessageCodes.STATUS_CHANGED, user={
                "login": self.login,
                "status": status
            }))
        return None


class AddFriendController(Controller):
    @logged
    def action(self, login):
        import connection
        conn = connection.ConnectionPool.get_connection()
        try:
            if self.login.login == login:
                return ReturnView(
                    type=MessageCodes.CANNOT_ADD_ITSELF
                )
            added = dao.FriendDAO.add_friend(user=dto.User(login=self.login.login),
                                             friend=dto.User(login=login), conn=conn)
        except dao.NotAUser as ex:
            if ex.login is self.login:
                raise Exception()
            else:
                return ReturnView(type=MessageCodes.FRIEND_DOESNT_EXIST)
        else:
            if added is True:
                Socket().add_observer(login=login, observer=self.context)
                return ReturnView(
                    type=MessageCodes.FRIEND_ADDED,
                    user={
                        "login": login,
                        "state": Socket().get_state(login=login).value
                    })
            else:
                return ReturnView(
                    type=MessageCodes.FRIENDSHIP_EXISTS
                )
        finally:
            connection.ConnectionPool.release_connection(conn=conn)


class RemoveFriendController(Controller):
    @logged
    def action(self, login):
        dao.FriendDAO.remove_friends(user=dto.User(login=self.login.login),
                                     friend=dto.User(login=login))
        Socket().remove_observer(login=login, observer=self.context)
        return None


class FindUsersController(Controller):
    @logged
    def action(self, login):
        users = [user.login for user in
                 dao.UserDAO.find_users(login=login, excluded_login=self.login.login)]
        if len(users) is 0:
            return ReturnView(type=MessageCodes.USERS_NOT_FOUND)
        else:
            return ReturnView(type=MessageCodes.USERS_FOUND, users=users)


class FetchFriendsController(Controller):
    @logged
    def action(self):
        friends = [
            {"login": user.login, "status": user.status, "state": Socket().get_state(user.login).value}
            for user in dao.FriendDAO.get_friends(user=dto.User(login=self.login.login))]
        return ReturnView(type=MessageCodes.FRIENDS_FETCHED, friends=friends)


class LoggedUserController(Controller):
    @logged
    def action(self):
        user = dao.UserDAO.get_user(login=self.login.login)
        return ReturnView(type=MessageCodes.LOGGED_USER, user={
            "login": user.login,
            "status": user.status
        })


class LogOutController(Controller):
    @logged
    def action(self):
        self.login.logout()
        return ReturnView(type=MessageTypes.LOGOUT)


controllers = {
    MessageTypes.LOGIN: LoggedInController,
    MessageTypes.REGISTER: RegisterController,
    MessageTypes.INCOMING_MESSAGE: IncomingMessageController,
    MessageTypes.CHANGE_STATUS: ChangeStatusController,
    MessageTypes.ADD_FRIEND: AddFriendController,
    MessageTypes.REMOVE_FRIEND: RemoveFriendController,
    MessageTypes.FIND_USERS: FindUsersController,
    MessageTypes.LOGGED_USER: LoggedUserController,
    MessageTypes.LOGOUT: LogOutController,
    MessageTypes.FETCH_FRIENDS: FetchFriendsController
}


class UserLeaf(User, websocket.WebSocketHandler):
    def send_message(self, message, sender):
        if sender is not self:  # the user that sent the message shouldn't become the message
            with self.mutex:
                if isinstance(message.type, MessageCodes):
                    message.fields['type'] = message.type.value
                self.write_message(message=message.fields)

    def send_notification(self, notification, type=None):
        with self.mutex_observer:
            for observer in self.observers:  # iterate over the observers
                if type == "disconnected":
                    observer.unregister_observer(observer=self)
                else:
                    if isinstance(notification.type, MessageCodes):
                        notification.fields['type'] = notification.type.value
                    observer.notify(notification=notification.fields)  # notify the observer

    def notify(self, notification):
        with self.mutex:
            self.write_message(json.dumps(notification))  # send notification

    def register_observer(self, observer):
        with self.mutex_observer:
            if self.observers.count(observer) is 0:
                self.observers.append(observer)  # add an observer to the object

    def unregister_observer(self, observer):
        with self.mutex_observer:
            if self.observers.count(observer) is 1:
                self.observers.remove(observer)
                return True
            return False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login = LoginObject()
        self.observers = []
        self.mutex = threading.RLock()
        self.mutex_observer = threading.RLock()
        self.authenticated = False

    def build_message(self, **kwargs):
        return json.dumps(kwargs)

    def _unrecognized_message(self):
        message = MessageParser.unrecognized_message()
        return message

    def on_message(self, message):
        with self.mutex:
            try:
                message = MessageParser.parse(message=message)  # tries to parse the received message
            except InvalidMessage:  # it's impossible
                self.write_message(self._unrecognized_message())  # client is notified
            else:
                try:
                    controller = controllers.get(MessageTypes(message['type']))
                    controller = controller(login=self.login, context=self)
                    del message['type']
                    return_value = controller.action(**message)
                    if return_value is not None:
                        if isinstance(return_value, ReturnView):
                            if isinstance(return_value.type, MessageCodes):
                                return_value.fields['type'] = return_value.type.value
                            elif isinstance(return_value.type, int) is False:
                                raise Exception()
                            self.write_message(message=return_value.fields)
                except ValueError:
                    self.write_message(self.build_message(type=MessageCodes.UNRECOGNIZED_MESSAGE.value))
                except AccessRestricted:
                    self.write_message(self.build_message(type=MessageCodes.ACCESS_RESTRICTED.value))

    def on_close(self, code=None, reason=None):
        with self.mutex:
            if self.login.logged is True:
                Socket().remove_user(user=self, login=self.login.login)
            self.send_notification(notification=None, type="disconnected")


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
            if len(self._users) is 1:
                return self._users[0]
            else:
                return self

    def notify(self, notification):
        self._iterate(func=lambda user: user.notify(notification=notification))

    def register_observer(self, observer):
        self._iterate(func=lambda user: user.register_observer(observer=observer))

    def send_message(self, message, sender):
        self._iterate(func=lambda user: user.send_message(message=message, sender=sender))

    def unregister_observer(self, observer):
        self._iterate(func=lambda user: user.unregister_observer(observer=observer))

    def close(self):
        self._iterate(func=lambda user: user.close())


class NoUser(Exception):
    pass


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
                leaf.send_notification(notification=ReturnView(
                    type=MessageCodes.STATE_CHANGED,
                    state=UserState.ACTIVE.value,
                    login=user.login
                ))
            elif isinstance(item, UserLeaf):
                item2 = UserComposite()
                item2.add_user(user=item)
                item2.add_user(user=leaf)
                item = item2
            elif isinstance(item, UserComposite):
                item.add_user(user=leaf)
            self._users[user.login] = item


    def unregister_observer(self, user):
        with self.mutex:
            for login, user in self._users.items():
                user.unregister_observer(observer=user)

    def remove_user(self, user, login):
        with self.mutex:
            if self._users.get(login) is None:
                raise NoUser()
            item = self._users[login]
            if isinstance(item, UserLeaf):
                user.send_notification(notification=ReturnView(
                    type=MessageCodes.STATE_CHANGED,
                    state=UserState.DISCONNECTED.value,
                    login=user.login.login
                ))
                del self._users[login]
            elif isinstance(item, UserComposite):
                self._users[login] = item.remove_user(user=user)

    def disconnect_users(self):
        with self.mutex:
            for login, user in self._users.items():
                user.close()

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
    try:
        app.listen(port=3000)
    except OSError:
        print("Address already in use")
        sys.exit(1)
    except Exception as ex:
        import traceback

        traceback.print_exc()
        sys.exit(1)
    dao.UserDAO.create_table()
    dao.MessageDAO.create_table()
    dao.FriendDAO.create_table()
    print("Listening on 0.0.0.0:3000")
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print("Closing the server")
        Socket().disconnect_users()
        sys.exit(0)
    except:
        import traceback

        traceback.print_exc()
        sys.exit(1)
