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
