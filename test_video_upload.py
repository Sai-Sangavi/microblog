import io
import os
import shutil
import tempfile
import unittest
import sqlalchemy as sa
from app import create_app, db
from app.models import Post
from test_comments import TestConfig, make_user


class VideoConfig(TestConfig):
    VIDEO_MAX_BYTES = 1024
    MAX_CONTENT_LENGTH = 1024 + 4096


def post_count():
    return db.session.scalar(sa.select(sa.func.count(Post.id)))


class VideoUploadTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        VideoConfig.VIDEO_UPLOAD_DIR = self.dir
        self.app = create_app(VideoConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = make_user()
        self.client = self.app.test_client()
        self.client.post("/auth/login", data={"username": "susan", "password": "cat"})
        self.pending = os.path.join(self.dir, "pending")

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        shutil.rmtree(self.dir, ignore_errors=True)

    def upload(self, name="clip.mp4", size=100, client=None):
        return (client or self.client).post(
            "/new_post/video",
            data={"video": (io.BytesIO(b"\x00" * size), name)},
            content_type="multipart/form-data",
        )

    def token(self):
        return self.upload().get_json()["token"]

    def pending_files(self):
        return os.listdir(self.pending) if os.path.isdir(self.pending) else []

    # AC1
    def test_upload_returns_token_and_publish_attaches_video(self):
        r = self.upload()
        self.assertEqual(r.status_code, 200)
        token = r.get_json()["token"]
        self.assertRegex(token, r"^[0-9a-f]{32}$")
        self.client.post(
            "/new_post", data={"body": "Our weekend hike.", "video_token": token}
        )
        p = db.session.scalar(sa.select(Post))
        self.assertEqual(p.body, "Our weekend hike.")  # AC6
        self.assertTrue(p.video_filename.endswith(".mp4"))

    def test_wrong_type_400_and_signed_out_302(self):
        self.assertEqual(self.upload("notes.txt").status_code, 400)
        self.assertEqual(self.upload(client=self.app.test_client()).status_code, 302)

    def test_other_users_token_not_promoted(self):
        token = self.token()
        make_user("bob")
        other = self.app.test_client()
        other.post("/auth/login", data={"username": "bob", "password": "cat"})
        r = other.post("/new_post", data={"body": "", "video_token": token})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(post_count(), 0)

    def test_bad_token_shapes_rejected(self):
        r = self.client.post(
            "/new_post", data={"body": "", "video_token": "../../etc/passwd"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(post_count(), 0)
        self.assertEqual(self.client.delete("/new_post/video/..%2Fx").status_code, 404)

    # AC2
    def test_limit_shown_before_upload(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r"MP4 or MOV, up to [^.]+\. One video per post\.")
        self.assertIn("Choose video file", html)
        self.assertEqual(self.pending_files(), [])

    def test_oversize_upload_413_json(self):
        r = self.upload(size=1024 + 8192)
        self.assertEqual(r.status_code, 413)
        self.assertIn("error", r.get_json())

    # AC3 / AC4 / AC8 / AC9 / AC10: markup smoke check only. There is no JS
    # runner, so the behaviour itself is verified manually in a browser; this
    # asserts the rendered DOM hooks the script relies on are present.
    def test_page_ships_progress_and_cancel_hooks(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r'<progress[^>]*max="100"')
        self.assertIn('role="status"', html)
        self.assertRegex(html, r'<button[^>]*id="publish"')
        self.assertIn("Publish turns on when the video has finished uploading.", html)
        self.assertIn("Cancel upload", html)
        self.assertRegex(html, r'<textarea[^>]*name="body"')
        self.assertRegex(html, r'<input[^>]*type="file"')

    def test_unknown_token_with_text_is_rejected(self):
        r = self.client.post("/new_post", data={"body": "hi", "video_token": "a" * 32})
        self.assertEqual(post_count(), 0)
        self.assertIn("finished uploading", r.get_data(as_text=True))

    # AC5 / AC6
    def test_publish_enabled_with_finished_video(self):
        token = self.token()
        # a too-long text forces a server re-display that keeps the token
        html = self.client.post(
            "/new_post", data={"body": "x" * 141, "video_token": token}
        ).get_data(as_text=True)
        self.assertNotRegex(html, r'<button[^>]*id="publish"[^>]*\bdisabled\b')
        self.assertIn(token, html)
        self.assertIn("Uploaded", html)

    # AC7
    def test_video_only_publish_goes_home_and_renders(self):
        token = self.token()
        r = self.client.post("/new_post", data={"body": "", "video_token": token})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            r.headers["Location"].endswith("/index") or r.headers["Location"] == "/"
        )
        p = db.session.scalar(sa.select(Post))
        self.assertEqual(p.body, "")
        self.assertEqual(self.pending_files(), [])
        self.assertTrue(
            os.path.exists(os.path.join(self.dir, "videos", p.video_filename))
        )
        self.assertIn("<video", self.client.get("/explore").get_data(as_text=True))
        v = self.client.get(f"/media/video/{p.video_filename}")
        self.assertEqual(v.status_code, 200)
        v.close()
        self.assertEqual(self.client.get("/media/video/..%2Fx").status_code, 404)

    def test_neither_text_nor_token_fails(self):
        r = self.client.post("/new_post", data={"body": "  ", "video_token": ""})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Write something before you publish.", r.get_data(as_text=True))
        self.assertEqual(post_count(), 0)

    # AC8 / AC9
    def test_cancel_discards_pending_and_text_publishes(self):
        token = self.token()
        self.assertEqual(
            self.client.delete(f"/new_post/video/{token}").status_code, 204
        )
        self.assertEqual(self.pending_files(), [])
        self.assertEqual(
            self.client.delete(f"/new_post/video/{token}").status_code, 204
        )
        self.client.post("/new_post", data={"body": "hi", "video_token": token})
        self.assertEqual(post_count(), 0)

    def test_text_only_after_discard_publishes_text(self):
        token = self.token()
        self.client.delete(f"/new_post/video/{token}")
        self.client.post("/new_post", data={"body": "hi"})
        p = db.session.scalar(sa.select(Post))
        self.assertEqual(p.body, "hi")
        self.assertIsNone(p.video_filename)

    def test_existing_post_without_video_still_renders(self):
        p = Post(body="old", author=self.user)
        db.session.add(p)
        db.session.commit()
        self.assertIsNone(db.session.get(Post, p.id).video_filename)
        self.assertEqual(self.client.get("/explore").status_code, 200)


if __name__ == "__main__":
    unittest.main()
