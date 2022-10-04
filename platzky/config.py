from os import path
import yaml


def get_babel_dir(raw_variable, directory):
    list_dir = raw_variable.split(";")
    new_babel_variable = ';'.join([path.join(directory, translation_dir) for translation_dir in list_dir])
    return new_babel_variable


def load_config(absolute_path):
    default_config = {
        "USE_WWW": True,
        "SEO_PREFIX": "/",
        "BLOG_PREFIX": "/"
    }
    with open(absolute_path, "r") as stream:
        file_config = yaml.safe_load(stream)

    config = default_config | file_config
    config["BABEL_TRANSLATION_DIRECTORIES"] = get_babel_dir(config["BABEL_TRANSLATION_DIRECTORIES"],
                                                            path.dirname(absolute_path))
    config["CONFIG_PATH"] = absolute_path
    return config
