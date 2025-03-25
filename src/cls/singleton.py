"""
This file holds a custom singleton class implementation that can be used to
create singleton instances of classes.
"""
import streamlit as st


class Singleton:
    """
    A class that can be used to create singleton instances of classes.

    This class should be inherited by the class that needs to be a singleton.
    Doing so ensures that only one instance of the class exists at any given time.
    """
    _instance = None

    @classmethod
    @st.cache_resource # Tell Streamlit to cache the resource across reruns
    def get_instance(cls, *args, **kwargs):
        """
        Get the singleton instance of the class.
        If the instance does not exist, it will be created.

        :return: The instance of the class.
        """
        if cls._instance is None:
            cls._instance = cls(*args, **kwargs)
        return cls._instance
