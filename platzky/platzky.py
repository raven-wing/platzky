import os
import yaml
from flask_babel import Babel
from flask import Flask, request, session, redirect, url_for
from .blog import blog, db_loader
from .plugin_loader import plugify

from flaskext.markdown import Markdown




def create_app(config_path):
    app = Flask(__name__)
    Markdown(app)
    absolute_config_path = os.path.join(os.getcwd(), config_path)
    app.config.from_file(absolute_config_path, load=yaml.safe_load)
    os.chdir(os.path.dirname(config_path))

    db_driver = db_loader.load_db_driver(app.config["DB"]["type"])
    app.db = db_driver.get_db(app.config["DB"])
    app.babel = Babel(app)

    blog_blueprint = blog.create_blog_blueprint(db=app.db,
                                                languages=app.config["LANG_MAP"],
                                                config=app.config,
                                                babel=app.babel)
    app.register_blueprint(blog_blueprint)

    # minify(app=app, html=True, js=True, cssless=True)


    @app.babel.localeselector
    def get_locale():
        return session.get('language', request.accept_languages.best_match(app.config["LANG_MAP"].keys()))

    @app.route('/language/<language>')
    def set_language(language):
        session['language'] = language
        return redirect(url_for('index'))

    return app #plugify(app)
