from unittest import TestCase
from connection import DBConnection, OperationNotAvailable, InvalidSavepointName, NoTransaction, NoExecObject, FetchAll


class TestDbConnection(TestCase):
    def test_cannot_begin_transaction_in_context(self):
        with DBConnection(db=':memory:') as conn:
            self.assertRaises(OperationNotAvailable, conn.begin_transaction)

    def test_cannot_commit_transaction_in_context(self):
        with DBConnection(db=':memory:') as conn:
            with self.assertRaises(OperationNotAvailable):
                conn.commit()

    def test_cannot_set_savepoint_in_context(self):
        with DBConnection(db=':memory:') as conn:
            with self.assertRaises(OperationNotAvailable):
                conn.savepoint(name='test')

    def test_savepoint_name_cannot_be_empty(self):
        conn = DBConnection(db=':memory:')
        conn.begin_transaction()
        with self.assertRaises(InvalidSavepointName):
            conn.savepoint(name='')

    def test_invalid_name_of_savepoint(self):
        conn = DBConnection(db=':memory:')
        conn.begin_transaction()
        with self.assertRaises(InvalidSavepointName):
            conn.savepoint(name='123')

    def test_exec_opts_is_not_a_subclass_of_execcommand(self):
        with DBConnection(db=':memory:') as conn:
            with self.assertRaises(NoExecObject):
                conn.exec("SELECT sqlite_version()", opts=type('object', (),dict()))

    def test_exec_opts_is_not_an_instance_of_execcommand(self):
        with DBConnection(db=':memory:') as conn:
            with self.assertRaises(NoExecObject):
                conn.exec("SELECT sqlite_version()", opts=type('object', (),dict()))

    def test_select(self):
        with DBConnection(db=':memory:') as conn:
            conn.exec("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT);")
            conn.exec("INSERT INTO t(name) VALUES ('name');")
            d = conn.exec("SELECT * FROM t", opts=FetchAll())
            self.assertEqual(d, [(1,'name')])

    def test_savepoint_unknown(self):
        conn = DBConnection(db=':memory:')
        conn.begin_transaction()
        conn.savepoint(name='save')
        with self.assertRaises(InvalidSavepointName):
            conn.rollback(name='sav')

