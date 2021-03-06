from datetime import datetime
from unittest import TestCase

import sys

from DBList import DBObject
from connection import DBConnection, ConnectionFactory, FetchAll
from dao import MessageDAO, UserDAO
from dto import Message, User


def transaction(func):
    def func_wrapper(*args):
        self = args[0]
        try:
            self.conn.begin_transaction()
            f = func(*args)
        except Exception as ex:
            raise ex
        finally:
            self.conn.commit()

    return func_wrapper


class TestMessageDAO(TestCase):
    def setUp(self):
        self.conn = ConnectionFactory.get_connection(db=":memory:")
        self.conn.begin_transaction()
        UserDAO.create_table(conn=self.conn)
        MessageDAO.create_table(conn=self.conn)
        self.conn.commit()

    @transaction
    def test_create_database(self):
        MessageDAO.create_table(conn=self.conn)

    @transaction
    def test_fetch_nonexistent_message(self):
        self.assertEqual(MessageDAO.get_message(conn=self.conn, id_message=sys.maxsize), None)

    def tearDown(self):
        del self.conn
