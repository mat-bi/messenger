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
        user = UserDAO.add_user(User(password='1234'), conn=connections[0])
        connections[0].commit()
        self.assertEqual(UserDAO.get_user(id_user=user.id_user, conn=connections[1]), User(id_user=user.id_user, password='1234'))
        self.assertEqual(UserDAO.get_user(id_user=user.id_user, conn=connections[2]), User(id_user=user.id_user, password='1234'))