from flask import redirect
from functools import partial


def process(app):
    redirects = app.db.get_redirections()
    for source, destiny in redirects.items():
        func = partial(redirect, destiny, code=301)
        func.__name__ = f"{source}-{destiny}"
        app.route(rule=source)(func)
    return app
