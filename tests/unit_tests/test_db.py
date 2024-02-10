import pytest

from platzky.db.db import DB

def test_db_extension():
    db = DB()

    with pytest.raises(AttributeError):
        db.test()
    db.extend("test", lambda x: "test")
    result = db.test()
    assert result == "test"


def test_db_doesnt_allow_its_children_to_add_new_methods():
    with pytest.raises(TypeError):
        class TestDB(DB):
            def test(self):
                return "test"
