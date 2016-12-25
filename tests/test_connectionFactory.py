from unittest import TestCase
from connection import ConnectionFactory, Connection


class TestConnectionFactory(TestCase):
    def test_is_a_connection_instance(self):
        connection = ConnectionFactory.get_connection()
        self.assertTrue(isinstance(connection, Connection))
