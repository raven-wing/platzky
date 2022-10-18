from platzky.platzky import *

def test_engine_creation():
    mapping = {'DB': {'type': 'json_file',
                      "PATH": "./tests/e2e_tests/db.json"}}
    engine = create_engine(config.from_mapping(mapping))
    assert type(engine) == Flask
