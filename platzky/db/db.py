from functools import partial
from typing import Any

from pydantic import BaseModel, Field

from abc import abstractmethod, ABC


class DB(ABC):
    def __init__(self):
        self.db_name: str = "DB"
        self.module_name: str = "db"
        self.config_type: type

    def __init_subclass__(cls, *args, **kw):
        super().__init_subclass__(*args, **kw)
        for name in cls.__dict__:
            if name.startswith('_'):
                continue
            for superclass in cls.__mro__[1:]:
                if name in dir(superclass):
                    break
            else:
                raise TypeError(
                    f"Method {name} defined in {cls.__name__} does not exist in superclasses"
                )
    def extend(self, function_name, function):
        """
        Add a function to the DB object. The function must take the DB object as first parameter.
        """
        bound = partial(function, self)
        setattr(self, function_name, bound)

    @abstractmethod
    def get_all_posts(self, lang) -> Any:
        pass

    @abstractmethod
    def get_menu_items(self):
        pass

    @abstractmethod
    def get_post(self, slug):
        pass

    @abstractmethod
    def get_page(self, slug):
        pass

    @abstractmethod
    def get_posts_by_tag(self, tag, lang) -> Any:
        pass

    @abstractmethod
    def add_comment(self, author_name, comment, post_slug):
        pass

    @abstractmethod
    def get_logo_url(self):
        pass

    @abstractmethod
    def get_primary_color(self):
        pass

    @abstractmethod
    def get_secondary_color(self):
        pass

    @abstractmethod
    def get_plugins_data(self):
        pass

    @abstractmethod
    def get_font(self):
        pass

    @abstractmethod
    def get_all_providers(self):  # TODO this should belong in plugin
        pass

    @abstractmethod
    def get_all_questions(self):  # TODO this should belong in plugin
        pass

    @abstractmethod
    def get_site_content(self):  # TODO this should not be public
        pass


class DBConfig(BaseModel):
    type: str = Field(alias="TYPE")
