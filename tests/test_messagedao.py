from unittest import TestCase

from connection import DBConnection, ConnectionPool
from dao import MessageDAO
from dto import Message


class TestMessageDAO(TestCase):
    def setUp(self):
        self.conn = ConnectionPool.get_connection(db=":memory:")
        self.conn.begin_transaction()
        MessageDAO.create_table(conn=self.conn)

    def test_fetch_one_message(self):
        self.assertEqual(MessageDAO.add_message(conn=self.conn,
                                                message=Message(id_user_to=1, id_user_from=1, content='First message',
                                                                unread=True)).id_message, 1)
        self.assertEqual((1, 'First message', 1, 1, True), MessageDAO.get_message(conn=self.conn, id_message=1))
        ConnectionPool.release_connection(conn=self.conn)

    def test_create_database(self):
        MessageDAO.create_table(conn=self.conn)

    def test_fetch_nonexistent_message(self):
        self.assertEqual(MessageDAO.get_message(conn=self.conn, id_message=10), None)

    def test_get_unread_messages(self):
        self.assertEqual(MessageDAO.add_message(message=Message(id_user_to=2, id_user_from=2, content='1', unread=True),
                                                conn=self.conn).id_message, 2)
        self.assertEqual(MessageDAO.add_message(message=Message(id_user_to=2, id_user_from=2, content='2', unread=True),
                                                conn=self.conn).id_message, 3)
        self.assertEqual(MessageDAO.get_unread_messages(conn=self.conn, id_user_to=2), [
            (2, '1', 2, 2, 1), (3, '2', 2, 2, 1)
        ])
        self.assertEqual(MessageDAO.get_unread_messages(conn=self.conn, id_user_to=2), [])

    def tearDown(self):
        del self.conn
