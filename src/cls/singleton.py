"""
This file holds a custom singleton class implementation that can be used to
create singleton instances of classes.
"""


class Singleton:
    """
    Ensures that a class has only one instance and provides a global point of access to that instance.

    This class implements the singleton pattern to ensure that only one instance of the class
    can exist throughout the lifetime of the application. Use the `get_instance` method
    to retrieve the instance.

    :ivar _instance: Holds the singleton instance of the class.
    :type _instance: type[Singleton] or None
    """
    _instance = None

    # TODO: Find a way to add the @st.cache_resource decorator back to the class method to cache the instances
    @classmethod
    #@st.cache_resource # Tell Streamlit to cache the resource across reruns
    def get_instance(cls, *args, **kwargs):
        """
        Provides a thread-safe singleton instance of the class. If an instance does
        not exist, it creates one using the provided arguments and keyword
        arguments. Otherwise, it returns the existing instance. This method uses
        a class-level attribute to store the singleton instance and ensures that
        the resource is cached across reruns using Streamlit's caching mechanism
        (if the commented decorator is uncommented).

        :param args: Positional arguments to be used for the instantiation of the
            class instance.
        :type args: tuple
        :param kwargs: Keyword arguments to be used for the instantiation of the
            class instance.
        :type kwargs: dict
        :return: Singleton instance of the class.
        :rtype: cls
        """
        if cls._instance is None:
            cls._instance = cls(*args, **kwargs)
        return cls._instance
