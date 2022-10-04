from functools import partial
import os
import yaml
from flask_babel import Babel
from flask import Flask, request, session, redirect, url_for, render_template
import urllib.parse

from .blog import blog, db_loader
from .seo import seo
from .plugin_loader import plugify
from . import default_config

from .www_handler import redirect_www_to_nonwww, redirect_nonwww_to_www

from flask_minify import Minify

from flaskext.markdown import Markdown


def create_app(config_path):
    engine = create_engine(config_path)
    blog_blueprint = blog.create_blog_blueprint(db=engine.db,
                                                config=engine.config, babel=engine.babel)
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
    app.config.from_mapping(default_config.defaults)
    app.config.from_file(absolute_config_path, load=yaml.safe_load)
    app.config["CONFIG_PATH"] = absolute_config_path
    db_driver = db_loader.load_db_driver(app.config["DB"]["type"])
    app.db = db_driver.get_db(app.config)
    app.babel = Babel(app)
    languages = app.config["LANG_MAP"]
    domain_langs = app.config["DOMAIN_TO_LANG"]

    @app.before_request
    def handle_www_redirection():
        if app.config["USE_WWW"]:
            return redirect_nonwww_to_www()
        else:
            return redirect_www_to_nonwww()

    @app.babel.localeselector
    def get_locale():
        domain = request.headers['Host']
        chosen_domain_lang = domain_langs.get(domain, request.accept_languages.best_match(languages.keys()))
        lang = session.get('language', chosen_domain_lang)
        session['language'] = lang
        return lang

    def get_langs_domain(lang):
        return languages.get(lang).get('domain')

    @app.route('/lang/<string:lang>', methods=["GET"])
    def change_language(lang):
        if new_domain := get_langs_domain(lang):
            return redirect("http://" + new_domain, code=301)
        else:
            session['language'] = lang
            return redirect("http://" + request.url)


    @app.context_processor
    def utils():
        return {
            "app_name": app.config["APP_NAME"],
            'languages': languages,
            "language": get_locale(),
            "url_link": lambda x: urllib.parse.quote(x, safe=''),
            "menu": app.db.get_menu()
        }

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html', title='404'), 404

    return plugify(app)
