import pytest
from src.main import greet

def test_greet():
    assert greet() == "Hello Transport-Projekt!"
