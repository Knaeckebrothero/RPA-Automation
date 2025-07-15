"""
Unit tests for the Singleton class.

This module contains tests for the Singleton class functionality, including
instance management and inheritance behavior.
"""
import pytest
from unittest.mock import patch

from cls.singleton import Singleton


class TestSingleton:
    """Test suite for the Singleton class."""

    def test_singleton_instance_creation(self):
        """Test that only one instance of a Singleton class is created."""
        # Create a test class that inherits from Singleton
        class TestClass(Singleton):
            def __init__(self, value=None):
                self.value = value

        # Get the first instance
        instance1 = TestClass.get_instance(value="test_value")
        
        # Get another instance
        instance2 = TestClass.get_instance()
        
        # Verify that both variables reference the same instance
        assert instance1 is instance2
        
        # Verify that the instance was initialized with the provided value
        assert instance1.value == "test_value"
        
        # Verify that the value wasn't changed when getting the second instance
        assert instance2.value == "test_value"

    def test_multiple_singleton_classes(self):
        """Test that different classes that inherit from Singleton have separate instances."""
        # Create two test classes that inherit from Singleton
        class TestClass1(Singleton):
            def __init__(self, value=None):
                self.value = value

        class TestClass2(Singleton):
            def __init__(self, value=None):
                self.value = value

        # Get instances of each class
        instance1 = TestClass1.get_instance(value="class1_value")
        instance2 = TestClass2.get_instance(value="class2_value")
        
        # Verify that the instances are different
        assert instance1 is not instance2
        
        # Verify that each instance has the correct value
        assert instance1.value == "class1_value"
        assert instance2.value == "class2_value"

    def test_singleton_with_different_arguments(self):
        """Test that subsequent calls to get_instance with different arguments don't change the instance."""
        # Create a test class that inherits from Singleton
        class TestClass(Singleton):
            def __init__(self, value=None):
                self.value = value

        # Get the first instance with one value
        instance1 = TestClass.get_instance(value="first_value")
        
        # Try to get another instance with a different value
        instance2 = TestClass.get_instance(value="second_value")
        
        # Verify that both variables reference the same instance
        assert instance1 is instance2
        
        # Verify that the value wasn't changed
        assert instance1.value == "first_value"
        assert instance2.value == "first_value"

    def test_singleton_reset(self):
        """Test resetting a Singleton class's instance."""
        # Create a test class that inherits from Singleton
        class TestClass(Singleton):
            def __init__(self, value=None):
                self.value = value

        # Get the first instance
        instance1 = TestClass.get_instance(value="test_value")
        
        # Reset the instance
        TestClass._instance = None
        
        # Get a new instance
        instance2 = TestClass.get_instance(value="new_value")
        
        # Verify that the instances are different
        assert instance1 is not instance2
        
        # Verify that the new instance has the new value
        assert instance2.value == "new_value"

    def test_singleton_inheritance_chain(self):
        """Test that the singleton pattern works through an inheritance chain."""
        # Create a chain of classes that inherit from Singleton
        class BaseClass(Singleton):
            def __init__(self, base_value=None):
                self.base_value = base_value

        class DerivedClass(BaseClass):
            def __init__(self, base_value=None, derived_value=None):
                super().__init__(base_value)
                self.derived_value = derived_value

        # Get instances of the derived class
        instance1 = DerivedClass.get_instance(base_value="base", derived_value="derived")
        instance2 = DerivedClass.get_instance()
        
        # Verify that both variables reference the same instance
        assert instance1 is instance2
        
        # Verify that the instance has the correct values
        assert instance1.base_value == "base"
        assert instance1.derived_value == "derived"