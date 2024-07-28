"""
This file holds a custom singleton class implementation that can be used to
create singleton instances of classes.
"""


class Singleton:
    _instance = None

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = cls(*args, **kwargs)
        return cls._instance
