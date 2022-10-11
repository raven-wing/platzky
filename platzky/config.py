from os import path
import yaml


def get_babel_dir_format(directory, raw_variable):
    list_dir = raw_variable.split(";")
    new_babel_variable = ';'.join([path.join(directory, translation_dir) for translation_dir in list_dir])
    return new_babel_variable


def load_config(absolute_config_path):
    default_config = {
        "USE_WWW": True,
        "SEO_PREFIX": "/",
        "BLOG_PREFIX": "/"
    }
    with open(absolute_config_path, "r") as stream:
        file_config = yaml.safe_load(stream)

    config = default_config | file_config
    translation_dirs = config.get("TRANSLATION_DIRECTORIES", []) + ["./locale"]
    config["BABEL_TRANSLATION_DIRECTORIES"] = ";".join(translation_dirs)
    config["CONFIG_PATH"] = absolute_config_path
    return config
