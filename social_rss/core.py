"""Core classes and tools."""

class Error(Exception):
    """The base class for all exceptions the module raises."""

    def __init__(self, *args, **kwargs):
        super(Error, self).__init__(args[0].format(*args[1:], **kwargs))
