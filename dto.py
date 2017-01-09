from abc import ABC, abstractproperty


class NoFieldsField(Exception):
    pass

class InvalidObject(Exception):
    pass


class DTO(ABC):

    @abstractproperty
    def fields(self):
        pass

    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    def __eq__(self, other):
        if isinstance(other, self.__class__) is False:
            return False

        for field in self.fields:
            if getattr(self, field) != getattr(other, field):
                return False
        return True


class Message(DTO):
    fields = [
        'id_message', 'content', 'creation_date', 'user'
    ]

    @staticmethod
    def from_json(json):
        if Message.fields not in json:
            raise InvalidObject()

        return Message(id_message=json['id_message'], content=json['content'], creation_date=json['creation_date'])


class User(DTO):
    fields = [
        'login', 'password'
    ]
