from unittest import TestCase

from dto import DTO


class TestDTO(TestCase):
    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            DTO()

    def _dto(self):
        return type('ClassDTO', (DTO,), {'fields': [
            'field1', 'field2'
        ]})

    def test_kwargs_become_kwargs(self):
        dto = self._dto()
        obj = dto(field1='field',field2='field2')
        self.assertEqual(obj.field1, 'field')
        self.assertEqual(obj.field2, 'field2')

    def test_can_instantiate_with_fields_set(self):
        dto = self._dto()
        dto()