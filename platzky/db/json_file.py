from platzky.blog.db import DB
import json
import datetime
import os.path

def get_db(config):
    db_path = os.path.join(os.path.dirname(config["CONFIG_PATH"]),
                           config["DB"]["PATH"])
    return JsonFile(db_path)


class JsonFile(DB):
    def __init__(self, file_path):
        self.file = file_path
        with open(self.file) as json_file:
            self.json = json.load(json_file)

    def _save_file(self):
        with open(self.file, 'w') as json_file:
            json.dump(self.json, json_file)

    def get_all_posts(self, lang):
        return self.json["posts"]

    def get_post(self, slug):
        post = next(filter(lambda x: x["slug"] == slug, self.json["posts"]))
        return post

    def get_page(self, slug, lang):
        post = next(filter(lambda x: x["slug"] == slug, self.json["pages"]))
        return post

    def get_posts_by_tag(self, tag, lang):
        posts = filter(lambda x: tag in x["tags"], self.json["posts"])
        return posts

    def get_all_providers(self):
        return self.json["providers"]

    def get_all_questions(self):
        return self.json["questions"]

    def get_redirections(self):
        return self.json["redirections"]

    def add_comment(self, author_name, comment, post_slug):
        comment = {
            "author": str(author_name),
            "comment": str(comment),
            "date": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }
        post_index = next(i for i in range(len(self.json["posts"])) if self.json["posts"][i]["slug"] == post_slug)
        self.json["posts"][post_index]["comments"].append(comment)
        self._save_file()
