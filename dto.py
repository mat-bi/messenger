class DTO:
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

class Message(DTO):
    pass

class User(DTO):
    pass
