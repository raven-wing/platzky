from flask import redirect
from functools import partial
from gql import gql


def graphql_get_redirections(self):
    redirections = gql(
        """
        query MyQuery{
          redirections(stage: PUBLISHED){
            source
            destination
          }
        }
        """
    )
    return {x['source']:x['destination'] for x in self.client.execute(redirections)['redirections']}


def process(app):
    app.db.get_redirections = graphql_get_redirections
    redirects = app.db.get_redirections(app.db)
    for source, destiny in redirects.items():
        func = partial(redirect, destiny, code=301)
        func.__name__ = f"{source}-{destiny}"
        app.route(rule=source)(func)

    return app
