from functools import partial
from typing import Any

from pydantic import BaseModel, Field


class DB:
    def __init__(self):
        self.db_name: str = "DB"
        self.module_name: str = "db"
        self.config_type: type

    def __init_subclass__(cls, *args, **kw):
        super().__init_subclass__(*args, **kw)
        for name, attr in cls.__dict__.items():
            attr = getattr(cls, name)
            if not callable(attr):
                continue
            for superclass in cls.__mro__[1:]:
                if name in dir(superclass):
                    break
            else:
                raise TypeError(f"Method {name} defined in {cls.__name__}  does not exist in superclasses")


    def extend(self, function_name, function):
        """
        Add a function to the DB object. The function must take the DB object as first parameter.
        """
        bound = partial(function, self)
        setattr(self, function_name, bound)

    def get_all_posts(self, lang) -> Any:
        pass

    def get_menu_items(self):
        pass

    def get_post(self, slug):
        pass

    def get_page(self, slug):
        pass

    def get_posts_by_tag(self, tag, lang) -> Any:
        pass

    def get_menu(self):
        pass

    def add_comment(self, author_name, comment, post_slug):
        pass

    def get_logo_url(self):
        pass

    def get_primary_color(self):
        pass

    def get_secondary_color(self):
        pass

    def get_plugins_data(self):
        pass

    def get_font(self):
        pass

    def get_all_providers(self):  # TODO this should belong in plugin
        pass

    def get_all_questions(self):  # TODO this should belong in plugin
        pass

    def get_site_content(self): # TODO this should not be public
        pass

    def _save_file(self): # TODO this should not be public
        pass

    def save_entry(self, entry): # TODO this should not be public
        pass

class DBConfig(BaseModel):
    type: str = Field(alias="TYPE")
