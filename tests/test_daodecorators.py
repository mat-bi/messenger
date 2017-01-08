import os
from unittest import TestCase

from connection import ConnectionFactory
from dao import UserDAO
from dto import User


class TestDAODecorators(TestCase):

    def test_transaction_no_connection(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, "db.db")
        connections = [ConnectionFactory.get_connection(db=db_path), ConnectionFactory.get_connection(db=db_path), ConnectionFactory.get_connection(db=db_path)]
        for conn in connections:
            conn.begin_transaction()
        UserDAO.create_table(conn=connections[0])
        connections[0].commit()
        connections[0].begin_transaction()
        user = UserDAO.register(login='test',password='1234', conn=connections[0])
        connections[0].commit()
        self.assertEqual(UserDAO.get_user(login=user.login, conn=connections[1]), User(login=user.login, password='1234'))
        self.assertEqual(UserDAO.get_user(login=user.login, conn=connections[2]), User(login=user.login, password='1234'))