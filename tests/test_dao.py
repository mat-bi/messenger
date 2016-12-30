from unittest import TestCase

from dao import DAO


class TestDAO(TestCase):

    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            DAO()

    def test_can_instantiate_with_create_table(self):
        def create_table(conn=None):
            pass
        dao = type('ClassDAO', (DAO,), {'create_table': create_table})
        dao()