from unittest import TestCase

from connection import ConnectionFactory
from dao import UserDAO
from dto import User


class TestUserDAO(TestCase):

    def setUp(self):
        self.conn = ConnectionFactory.get_connection(db=':memory:')
        self.conn.begin_transaction()
        UserDAO.create_table(conn=self.conn)

    def test_get_user(self):
        self.assertEqual(UserDAO.add_user(User(password='1234'),conn=self.conn).id_user, 1001)
        self.assertEqual(UserDAO.get_user(id_user=1001, conn=self.conn), User(id_user=1001, password='1234'))

    def tearDown(self):
        del self.conn