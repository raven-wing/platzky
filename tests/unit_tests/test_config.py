from platzky.config import *
import pytest


def test_config_creation_with_incorrect_mappings():
    empty_mapping = {}
    with pytest.raises(Exception):
        from_mapping(empty_mapping)

    db_without_type = {'DB': 'anything'}
    with pytest.raises(Exception):
        from_mapping(db_without_type)

    db_type_wrong = {'DB': {'type':'wrong-type'}}
    with pytest.raises(Exception):
        from_mapping(db_type_wrong)


def test_config_creation_from_mapping():
    not_empty_dict = {'DB': {'type': 'json_file'}}
    config = from_mapping(not_empty_dict)
    assert type(config) == Config
