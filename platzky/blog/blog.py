import urllib.parse
import os

from flask import Flask, request, render_template, current_app, redirect, send_from_directory, make_response, url_for, Blueprint
from flask_babel import Babel


#from secure import SecureHeaders

from platzky.blog import comment_form, post_formatter




def create_blog_blueprint(db, languages, config, babel):
    blog = Blueprint('blog', __name__, url_prefix="/blog")
    main_domain = config["MAIN_DOMAIN"]
    # secure_headers = SecureHeaders()


    # @blog.before_request
    # def redirect_nonwww():
    #     """Redirect non-www requests to www."""
    #     urlparts = urllib.parse.urlparse(request.url)
    #     if not urlparts.netloc.startswith("www."):
    #         urlparts = urlparts._replace(netloc=f'www.{urlparts.netloc}')
    #         return redirect(urllib.parse.urlunparse(urlparts), code=301)

    # @blog.after_request
    # def set_secure_headers(response):
    #     # secure_headers.flask(response)
    #     return response

    def domains_locale(dom):
        return config["DOMAIN_TO_LANG"][dom]

    @blog.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html', 404)

    @babel.localeselector
    def get_locale():
        return domains_locale(request.host)

    @blog.context_processor
    def utils():
        return {'languages': languages,
                "language": get_locale(),
                "url_link": lambda x: urllib.parse.quote(x, safe='')
                }

    @blog.route('/', methods=["GET"])
    def index():
        lang = get_locale()
        return render_template("blog.html", posts=db.get_all_posts(lang))

    @blog.route('/feed', methods=["GET"])
    def get_feed():
        lang = get_locale()

        response = make_response(render_template("feed.xml", posts=db.get_all_posts(lang)))
        response.headers["Content-Type"] = "application/xml"
        return response

    @blog.route('/<post_slug>', methods=["GET", "POST"])
    def get_post(post_slug):
        if request.method == "POST":
            comment = request.form.to_dict()
            db.add_comment(post_slug=post_slug, author_name=comment["author_name"],
                                            comment=comment["comment"])
            return redirect(url_for('get_post', post_slug=post_slug, comment_sent=True))
        raw_post = db.get_post(post_slug)

        return render_template("post.html", post=post_formatter.format_post(raw_post), post_slug=post_slug,
                               form=comment_form.CommentForm(), comment_sent=request.args.get('comment_sent'))

    @blog.route('/page/<path:page_slug>', methods=["GET", "POST"])
    def get_page(page_slug):
        return render_template("page.html", post=db.get_page(page_slug))


    @blog.route('/tag/<path:tag>', methods=["GET"])
    def get_posts_from_tag(tag):
        lang = get_locale()
        posts = db.get_posts_by_tag(tag, lang)
        return render_template("blog.html", posts=posts, subtitle=f" - tag: {tag}")

    @blog.route('/lang/<string:lang>', methods=["GET"])
    def change_language(lang):
        new_domain = blog.get_langs_domain(lang)
        return redirect("http://" + new_domain, code=301)

    @blog.route('/results', methods=["POST"])
    def render_answers():
        answers = {}
        required_fields = current_app.config['fields']
        for field, value in request.form.to_dict().items():
            if field not in required_fields:
                continue
            answers[field] = value
        return redirect(url_for('get_results', **answers))

    @blog.route('/results', methods=["GET"])
    def get_results():
        answers = {}
        fields = current_app.config['fields']
        for field, value in request.args.items():
            answers[field] = request.args.get(field)
        answers['subscribers_limit'] = int(answers['subscribers_limit'])  # TODO change either logic or move it somewhere else
        best_reults = get_best(answers)
        return render_template("result.html", best_list=best_reults, fields=fields, answers=answers)

    @blog.route('/icon/<string:name>', methods=["GET"])
    def icon(name):
        return send_from_directory('../static/icons', f"{name}.png")

    @blog.route("/robots.txt")
    def robots():
        robots_response = render_template("robots.txt", domain=request.host, mimetype='text/plain')
        response = make_response(robots_response)
        response.headers["Content-Type"] = "text/plain"
        return response

    @blog.route("/sitemap.xml", host=languages['pl']['domain'])
    def pl_sitemap():
        return sitemap('pl')

    @blog.route("/sitemap.xml", host=main_domain)
    def main_sitemap():
        return sitemap('en')

    def sitemap(lang):
        """
        Route to dynamically generate a sitemap of your website/application.
        lastmod and priority tags omitted on static pages.
        lastmod included on dynamic content such as blog posts.
        """

        global url
        host_components = urllib.parse.urlparse(request.host_url)
        host_base = host_components.scheme + "://" + host_components.netloc

        # Static routes with static content
        static_urls = list()
        for rule in blog.url_map.iter_rules():
            if not str(rule).startswith("/admin") and not str(rule).startswith("/user"):
                if "GET" in rule.methods and len(rule.arguments) == 0:
                    url = {
                        "loc": f"{host_base}{str(rule)}"
                    }
                static_urls.append(url)

        # Dynamic routes with dynamic content
        dynamic_urls = list()
        blog_posts = db.get_all_posts(lang)
        for post in blog_posts:
            slug = post['slug']
            datet = post['date'].split('T')[0]
            url = {
                "loc": f"{host_base}/blog/{slug}",
                "lastmod": datet
            }
            dynamic_urls.append(url)

        statics = list({v['loc']: v for v in static_urls}.values())
        dynamics = list({v['loc']: v for v in dynamic_urls}.values())
        xml_sitemap = render_template("sitemap.xml", static_urls=statics, dynamic_urls=dynamics,
                                      host_base=host_base)
        response = make_response(xml_sitemap)
        response.headers["Content-Type"] = "application/xml"
        return response

    return blog
















#
#
# class MainApp(Flask):
#     def __init__(self, config):
#         super().__init__(__name__, static_folder=None)
#         self.url_map.host_matching = True
#         self.config.update(config)
#         self.config["BABEL_TRANSLATION_DIRECTORIES"] = os.path.join(os.path.dirname(os.path.realpath(__file__)),
#                                                                     "../locale") #TODO create poetry plugin and let it handle this
#         app_engine_init()
#
#         self.babel = Babel(self)
#         # self.mail = Mail()
#         self.db = get_db(config["DB"])
#         questions = self.db.get_all_questions()
#         self.questions = questioner.get_questions(questions, config["fields"])
#         self.language_map = config["LANG_MAP"]
#
#         self.accepted_languages = self.language_map.keys()
#         self.providers = self.db.get_all_providers()
#         Markdown(self)
#
#     def does_lang_has_domain(self, lang):
#         return 'domain' in self.language_map.get(lang)
#
#     def get_langs_domain(self, lang):
#         if self.does_lang_has_domain(lang):
#             return self.language_map.get(lang)['domain']
#         else:
#             return self.config['MAIN_DOMAIN']
#
#     def domains_locale(self, dom):
#         return self.config["DOMAIN_TO_LANG"][dom]
#
#     def multi_route(self, *args, **kwargs):
#         def insider(func):
#             for domain in self.config["DOMAINS"]:
#                 self.add_url_rule(*args, endpoint=func.__name__, view_func=func, **kwargs, host=domain)
#             return func
#
#         return insider
