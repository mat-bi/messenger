from datetime import datetime
from unittest import TestCase

import sys

from DBList import DBObject
from connection import DBConnection, ConnectionFactory, FetchAll
from dao import MessageDAO, UserDAO
from dto import Message, User


class TestMessageDAO(TestCase):
    def setUp(self):
        self.conn = ConnectionFactory.get_connection(db=":memory:")
        self.conn.begin_transaction()
        MessageDAO.create_table(conn=self.conn)

    def test_fetch_one_message(self):
        user = User(password='1234')
        user = UserDAO.add_user(user, conn=self.conn)
        message = MessageDAO.add_message(
            Message(content='First message', id_user=DBObject(UserDAO.get_user, id_user=user.id_user, conn=self.conn)),
            conn=self.conn)
        message2 = MessageDAO.get_message(conn=self.conn, id_message=message.id_message)
        self.assertEqual(message, message2)

    def test_create_database(self):
        MessageDAO.create_table(conn=self.conn)

    def test_fetch_nonexistent_message(self):
        self.assertEqual(MessageDAO.get_message(conn=self.conn, id_message=sys.maxsize), None)

    def tearDown(self):
        del self.conn
