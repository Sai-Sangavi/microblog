import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from app import create_app, db
from app.models import Post
from test_comments import TestConfig, make_user


def post_count():
    return db.session.scalar(sa.select(sa.func.count(Post.id)))


class NewPostTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = make_user()
        self.client = self.app.test_client()
        self.client.post("/auth/login", data={"username": "susan", "password": "cat"})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_nav_has_new_post_entry_and_page_loads(self):
        home = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/new_post"', home)
        r = self.client.get("/new_post")
        self.assertEqual(r.status_code, 200)
        self.assertIn("<h1", r.get_data(as_text=True))

    def test_signed_out_has_no_new_post_entry_and_is_redirected(self):
        anon = self.app.test_client()
        self.assertNotIn(
            'href="/new_post"',
            anon.get("/explore", follow_redirects=True).get_data(as_text=True),
        )
        self.assertEqual(anon.get("/new_post").status_code, 302)

    def test_text_field_has_label_and_placeholder(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r'<label for="body"[^>]*>\s*Post text\s*</label>')
        self.assertIn('placeholder="What is on your mind?"', html)

    def test_text_field_is_empty_on_open(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r'<textarea[^>]*id="body"[^>]*>\s*</textarea>')
        self.assertNotRegex(html, r"<textarea[^>]*>[^<]*What is on your mind")

    def test_publish_disabled_when_empty(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r'<button[^>]*id="publish"[^>]*\bdisabled\b')

    def test_publish_enabled_when_text_present(self):
        with patch.object(db.session, "add", side_effect=SQLAlchemyError):
            html = self.client.post("/new_post", data={"body": "hi"}).get_data(
                as_text=True
            )
        self.assertNotRegex(html, r'<button[^>]*id="publish"[^>]*\bdisabled\b')
        self.assertIn("document.getElementById", html)

    def test_publish_redirects_home(self):
        r = self.client.post("/new_post", data={"body": "Hello there"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            r.headers["Location"].endswith("/index") or r.headers["Location"] == "/"
        )
        self.assertEqual(
            db.session.scalar(
                sa.select(sa.func.count(Post.id)).where(Post.body == "Hello there")
            ),
            1,
        )

    def test_posted_toast_shown_on_home(self):
        html = self.client.post(
            "/new_post", data={"body": "Hello there"}, follow_redirects=True
        ).get_data(as_text=True)
        self.assertRegex(html, r'class="toast is-open"[^>]*>\s*Posted\s*<')
        again = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('id="posted-toast"', again)

    def test_cancel_links_to_home_and_saves_nothing(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(
            html, r'<a[^>]*class="btn btn-secondary"[^>]*href="/"?[^"]*"[^>]*>\s*Cancel'
        )
        self.assertEqual(post_count(), 0)

    def test_whitespace_only_is_rejected(self):
        r = self.client.post("/new_post", data={"body": "  \r\n \n "})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Write something before you publish.", r.get_data(as_text=True))
        self.assertEqual(post_count(), 0)

    def test_new_post_is_first_on_home(self):
        db.session.add(
            Post(
                body="older post",
                author=self.user,
                timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
            )
        )
        db.session.commit()
        html = self.client.post(
            "/new_post", data={"body": "brand new"}, follow_redirects=True
        ).get_data(as_text=True)
        self.assertLess(html.index("brand new"), html.index("older post"))

    def test_publish_failure_keeps_page_text_and_shows_error(self):
        with patch.object(db.session, "add", side_effect=SQLAlchemyError):
            r = self.client.post("/new_post", data={"body": "keep me"})
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertRegex(html, r"<textarea[^>]*>\s*keep me\s*</textarea>")
        self.assertRegex(html, r'class="alert alert-danger"[^>]*role="alert"')
        self.assertIn("Your post didn&#39;t publish", html)
        self.assertEqual(post_count(), 0)

    def test_toast_declares_three_second_dismissal(self):
        html = self.client.post(
            "/new_post", data={"body": "Hello"}, follow_redirects=True
        ).get_data(as_text=True)
        self.assertIn('data-dismiss-ms="3000"', html)
        self.assertIn("setTimeout", html)

    def test_non_toast_flash_still_renders_as_alert(self):
        p = Post(body="hello world", author=self.user)
        db.session.add(p)
        db.session.commit()
        html = self.client.post(
            f"/post/{p.id}", data={"body": "Nice"}, follow_redirects=True
        ).get_data(as_text=True)
        self.assertIn('class="alert alert-info"', html)
        self.assertNotIn('id="posted-toast"', html)


if __name__ == "__main__":
    unittest.main()
