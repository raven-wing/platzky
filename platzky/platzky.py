import os
import yaml
from flask_babel import Babel
from flask import Flask, request, session, redirect, url_for, render_template
import urllib.parse

from .blog import blog, db_loader
from .seo import seo
from .plugin_loader import plugify
from . import config

from .www_handler import redirect_www_to_nonwww, redirect_nonwww_to_www

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
    languages = app.config["LANG_MAP"]

    @app.babel.localeselector
    def get_locale():
        return session.get('language', request.accept_languages.best_match(app.config["LANG_MAP"].keys()))

    @app.before_request
    def handle_www_redirection():
        if app.config["USE_WWW"]:
            return redirect_nonwww_to_www()
        else:
            return redirect_www_to_nonwww()

    def does_lang_has_domain(self, lang):
        return 'domain' in self.language_map.get(lang)

    def get_langs_domain(lang):
        if does_lang_has_domain(lang):
            return app.config["LANG_MAP"].get(lang)['domain']
        else:
            return config['MAIN_DOMAIN']

    def domains_locale(dom):
        return config["DOMAIN_TO_LANG"][dom]

    @app.route('/lang/<string:lang>', methods=["GET"])
    def change_language(lang):
        new_domain = get_langs_domain(lang)
        return redirect("http://" + new_domain, code=301)

    @app.context_processor
    def utils():
        return {'languages': languages,
                "language": get_locale(),
                "url_link": lambda x: urllib.parse.quote(x, safe='')
                }

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html', title='404'), 404

    @app.route('/language/<language>')
    def set_language(language):
        session['language'] = language
        return redirect(url_for('index'))
    return plugify(app)
