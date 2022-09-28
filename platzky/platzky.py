import os
import yaml
from flask_babel import Babel
from flask import Flask, request, session, redirect, url_for
from .blog import blog, db_loader
from .seo import seo
from .plugin_loader import plugify
from . import config

from flask_minify import Minify

from flaskext.markdown import Markdown


def create_app(config_path):
    engine = create_engine(config_path)
    blog_blueprint = blog.create_blog_blueprint(db=engine.db,
                                                config=engine.config,
                                                babel=engine.babel)
    seo_blueprint = seo.create_seo_blueprint(db=engine.db,
                                             config=engine.config)
    engine.register_blueprint(blog_blueprint)
    engine.register_blueprint(seo_blueprint)
    Minify(app=engine, html=True, js=True, cssless=True)

    return engine


def create_engine(config_path):
    app = Flask(__name__)
    Markdown(app)
    absolute_config_path = os.path.join(os.getcwd(), config_path)
    app.config.from_mapping(config.defaults)
    app.config.from_file(absolute_config_path, load=yaml.safe_load)
    app.config["CONFIG_PATH"] = absolute_config_path
    db_driver = db_loader.load_db_driver(app.config["DB"]["type"])
    app.db = db_driver.get_db(app.config)
    app.babel = Babel(app)

    @app.babel.localeselector
    def get_locale():
        return session.get('language', request.accept_languages.best_match(app.config["LANG_MAP"].keys()))

    @app.route('/language/<language>')
    def set_language(language):
        session['language'] = language
        return redirect(url_for('index'))
    return plugify(app)
