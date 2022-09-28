import os
import yaml
from flask_babel import Babel
from flask import Flask, request, session, redirect, url_for
from .blog import blog, db_loader
from .seo import seo
from .plugin_loader import plugify
from flask_minify import Minify

from flaskext.markdown import Markdown


def create_app(config_path):
    app = Flask(__name__)
    Markdown(app)
    # print(os.getcwd())
    absolute_config_path = os.path.join(os.getcwd(), config_path)

    app.config.from_file(absolute_config_path, load=yaml.safe_load)
    app.config["CONFIG_PATH"] = absolute_config_path
    db_driver = db_loader.load_db_driver(app.config["DB"]["type"])
    app.db = db_driver.get_db(app.config)
    app.babel = Babel(app)

    blog_blueprint = blog.create_blog_blueprint(db=app.db,
                                                config=app.config,
                                                babel=app.babel,
                                                url_prefix="/")

    seo_blueprint = seo.create_seo_blueprint(db=app.db,
                                             config=app.config,
                                             url_prefix="/")
    app.register_blueprint(blog_blueprint)
    app.register_blueprint(seo_blueprint)

    Minify(app=app, html=True, js=True, cssless=True)



    @app.babel.localeselector
    def get_locale():
        return session.get('language', request.accept_languages.best_match(app.config["LANG_MAP"].keys()))

    @app.route('/language/<language>')
    def set_language(language):
        session['language'] = language
        return redirect(url_for('index'))
    return plugify(app)
