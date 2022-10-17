from flask import redirect
from functools import partial
from gql import gql


def json_get_redirections(self):
    return self.json["redirections"]

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


def get_proper_redirections(db_type):
    redirections = {
        "json_file": json_get_redirections,
        "graphQl": graphql_get_redirections
    }
    return redirections[db_type]

def process(app):
    app.db.get_redirections = get_proper_redirections(app.config["DB"]["type"])
    redirects = app.db.get_redirections(app.db)
    for source, destiny in redirects.items():
        func = partial(redirect, destiny, code=301)
        func.__name__ = f"{source}-{destiny}"
        app.route(rule=source)(func)

    return app
