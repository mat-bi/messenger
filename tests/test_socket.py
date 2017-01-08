from unittest import TestCase

from dto import User
from main import Socket, NoUser, UserLeaf
import json


class TestSocket(TestCase):
    def setUp(self):
        self.socket = Socket()

    def test_only_one_instance(self):
        socket = (Socket(), Socket())
        self.assertEqual(socket[0], socket[1])

    def test_remove_raises_exception(self):
        with self.assertRaises(NoUser):
            self.socket.remove_user(UserLeaf(conn=None, addr=None, login='login'), 1234)

    def test_remove_existing_user(self):
        self.socket.add_user(user=User(login='login'), addr=None, conn=None)
        self.socket.remove_user(user=UserLeaf(conn=None, addr=None, login='login'), login='login')

    def test_build_message(self):
        self.assertEqual(Socket().build_message(message=1234), json.dumps({"message": 1234}))
        self.assertEqual(Socket().build_message(param1='param', param2='another_param',
                                                bizarre_name_with_many_characters=None),
                         json.dumps({"param1": 'param', "param2": "another_param",
                                     "bizarre_name_with_many_characters": None}))
