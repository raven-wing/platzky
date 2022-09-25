import os
import sys
from os.path import dirname, abspath
from importlib.util import spec_from_file_location, module_from_spec


def load_db_driver(db_type):
    db_dir = os.path.join(dirname(dirname(abspath(__file__))), 'db')
    spec = spec_from_file_location(db_type, os.path.join(db_dir, db_type + ".py"))
    db_driver = module_from_spec(spec)
    sys.modules[db_type] = db_driver
    spec.loader.exec_module(db_driver)
    return db_driver
