from unittest import TestCase

from connection import ConnectionFactory
from dao import UserDAO
from dto import User


class TestUserDAO(TestCase):

    def setUp(self):
        self.conn = ConnectionFactory.get_connection(db=':memory:')
        self.conn.begin_transaction()
        UserDAO.create_table(conn=self.conn)
        self.conn.commit()

    def test_get_user(self):
        self.assertEqual(UserDAO.register(login='test',password='1234',conn=self.conn).login, 'test')
        self.conn.begin_transaction()
        user = UserDAO.get_user(login='test', conn=self.conn)
        self.assertEqual(user.login, 'test')
        self.assertEqual(user.password, '1234')
        self.conn.commit()

    def tearDown(self):
        del self.conn