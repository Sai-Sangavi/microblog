import unittest
from datetime import datetime, timezone, timedelta
import sqlalchemy as sa
from app import create_app, db
from app.models import User, Post, Comment
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    ELASTICSEARCH_URL = None
    WTF_CSRF_ENABLED = False


def make_user(name="susan"):
    u = User(username=name, email=f"{name}@example.com")
    u.set_password("cat")
    db.session.add(u)
    db.session.commit()
    return u


def make_comment(post, user, body, ts=None):
    c = Comment(body=body, post=post, author=user)
    if ts is not None:
        c.timestamp = ts
    db.session.add(c)
    db.session.commit()
    return c


def count():
    return db.session.scalar(sa.select(sa.func.count(Comment.id)))


class CommentTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = make_user()
        self.post = Post(body="hello world", author=self.user)
        db.session.add(self.post)
        db.session.commit()
        self.url = f"/post/{self.post.id}"
        self.client = self.app.test_client()
        self.client.post("/auth/login", data={"username": "susan", "password": "cat"})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def page(self, post=None):
        post = post or self.post
        return self.client.get(f"/post/{post.id}").get_data(as_text=True)

    def anon(self):
        return self.app.test_client()

    def test_signed_in_comment_appears(self):
        r = self.client.post(self.url, data={"body": "Nice run"}, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Nice run", r.get_data(as_text=True))
        self.assertEqual(count(), 1)

    def test_signed_out_has_no_form(self):
        html = self.anon().get(self.url).get_data(as_text=True)
        self.assertNotIn("<textarea", html)
        self.assertNotIn('name="body"', html)

    def test_signed_in_sees_form(self):
        html = self.page()
        self.assertIn("<textarea", html)
        self.assertIn("Post comment", html)

    def test_comments_are_listed(self):
        make_comment(self.post, self.user, "alpha text")
        make_comment(self.post, self.user, "beta text")
        html = self.anon().get(self.url).get_data(as_text=True)
        self.assertIn("alpha text", html)
        self.assertIn("beta text", html)

    def test_post_page_404_for_unknown_post(self):
        self.assertEqual(self.client.get("/post/999").status_code, 404)

    def test_comments_are_one_flat_list(self):
        for i in range(3):
            make_comment(self.post, self.user, f"c{i}")
        html = self.page()
        self.assertEqual(html.count('<ol class="comment-list"'), 1)
        self.assertEqual(html.count('class="comment"'), 3)
        self.assertNotIn("parent_id", Comment.__table__.columns)

    def test_comments_oldest_first(self):
        now = datetime.now(timezone.utc)
        make_comment(self.post, self.user, "third body", now)
        make_comment(self.post, self.user, "second body", now - timedelta(hours=1))
        make_comment(self.post, self.user, "first body", now - timedelta(hours=2))
        html = self.page()
        self.assertLess(html.index("first body"), html.index("second body"))
        self.assertLess(html.index("second body"), html.index("third body"))

    def test_same_timestamp_ordered_by_id(self):
        now = datetime.now(timezone.utc)
        make_comment(self.post, self.user, "same one", now)
        make_comment(self.post, self.user, "same two", now)
        html = self.page()
        self.assertLess(html.index("same one"), html.index("same two"))

    def test_empty_comment_rejected(self):
        for body in ("", "   "):
            r = self.client.post(self.url, data={"body": body})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(count(), 0)
            self.assertIn("Write something before you post.", r.get_data(as_text=True))

    def test_comment_of_exactly_1000_chars_is_saved(self):
        body = "a" * 1000
        r = self.client.post(self.url, data={"body": body}, follow_redirects=True)
        self.assertIn(body, r.get_data(as_text=True))
        self.assertEqual(count(), 1)

    def test_comment_of_1001_chars_is_rejected(self):
        body = "a" * 1001
        r = self.client.post(self.url, data={"body": body})
        self.assertEqual(count(), 0)
        html = r.get_data(as_text=True)
        self.assertIn("This comment is too long", html)
        self.assertIn(body, html)

    def test_signed_out_sees_login_prompt(self):
        html = self.anon().get(self.url).get_data(as_text=True)
        self.assertIn("Log in to comment", html)

    def test_signed_out_post_is_not_saved(self):
        r = self.anon().post(self.url, data={"body": "sneaky"})
        self.assertEqual(count(), 0)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/auth/login", r.headers["Location"])

    def test_login_prompt_links_to_sign_in(self):
        html = self.anon().get(self.url).get_data(as_text=True)
        self.assertRegex(html, r'<a href="/auth/login[^"]*">\s*Log in to comment')

    def test_comment_shows_author_timestamp_and_text(self):
        other = make_user("bobby")
        make_comment(self.post, other, "bobby says hi")
        html = self.page()
        row = html[html.index('class="comment"') :]
        self.assertIn("bobby", row)
        self.assertIn("bobby says hi", row)
        self.assertIn("data-timestamp", row)

    def test_comment_body_is_escaped(self):
        make_comment(self.post, self.user, "<script>alert(1)</script>")
        self.assertNotIn("<script>alert(1)</script>", self.page())

    def test_no_comments_message(self):
        self.assertIn("No comments yet", self.page())
        make_comment(self.post, self.user, "something")
        self.assertNotIn("No comments yet", self.page())


if __name__ == "__main__":
    unittest.main()
