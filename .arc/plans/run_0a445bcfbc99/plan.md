summary: |
  Extend the existing New post page (app/templates/new_post.html, route main.new_post) so a signed-in member can choose one video (MP4/MOV), see the size limit before anything uploads, watch a progress bar while it uploads, cancel the upload (video removed, text kept, Choose video shown again), and publish once the upload has finished, with text optional when a video is attached. The upload goes through the Flask app (XHR POST to a new endpoint, so the browser gives real progress events) into a per-user pending area; Publish carries an opaque video token that the server verifies and promotes onto the new Post (new nullable Post.video_filename column + Alembic migration). Home/post rendering shows the published video. Failure handling and resume are explicitly out (STORY-015).
scope:
  - description: |
      Config: add `VIDEO_MAX_BYTES = int(os.environ.get('VIDEO_MAX_BYTES') or 500 * 1024 * 1024)`, `VIDEO_UPLOAD_DIR = os.environ.get('VIDEO_UPLOAD_DIR') or os.path.join(basedir, 'uploads')` and `MAX_CONTENT_LENGTH = VIDEO_MAX_BYTES + 1024 * 1024` (slack for multipart overhead and the CSRF/text fields). Allowed extensions `.mp4`, `.mov` live in one constant `ALLOWED_VIDEO_EXTENSIONS` (app/main/videos.py) so the limit text and server check share it.
    files:
      - config.py
    rationale: Settings per ADR-0012 (env vars, safe defaults). MAX_CONTENT_LENGTH makes Flask reject oversize bodies with 413 before reading them all.
  - description: |
      Model + migration: add `video_filename: so.Mapped[Optional[str]] = so.mapped_column(sa.String(64))` to Post. New Alembic revision (down_revision = "b2d4f6a8c0e1", the comments migration, the current head) adding a nullable column via `op.batch_alter_table("post")` (SQLite local / PostgreSQL prod), with downgrade dropping it.
    files:
      - app/models.py
      - migrations/versions/c3e5a7b9d1f2_post_video.py
    rationale: Nullable column, so every existing text-only post stays valid; no backfill.
  - description: |
      Video storage helper (new module app/main/videos.py), pure functions that touch only VIDEO_UPLOAD_DIR:
      ```python
      def save_pending(user_id: int, file_storage) -> str | None   # returns token, None if extension not allowed
      def delete_pending(user_id: int, token: str) -> bool
      def promote(user_id: int, token: str) -> str | None          # moves pending -> final, returns video_filename
      ```
      Token = `uuid4().hex`; file stored as `pending/<user_id>-<token><ext>`; token is validated with a hex regex before any path is built (no path traversal) and must belong to the calling user.
    files:
      - app/main/videos.py
    rationale: Keeps filesystem logic out of the routes and unit-testable. Local disk is the SQLite-local/dev store; production storage (S3 on AWS per ADR-0008) is an open question below.
  - description: |
      Routes (app/main/routes.py), all `@login_required`:
      - `POST /new_post/video` (name `upload_video`): CSRF-protected (X-CSRFToken header or form field), reads `request.files["video"]`; 400 `{"error": ...}` for wrong type, 413 handled by an errorhandler returning JSON for this path; 200 `{"token": "<hex>"}`.
      - `DELETE /new_post/video/<token>` (name `discard_video`): removes the pending file, 204. Used by Cancel upload (also safe to call for a token that no longer exists).
      - `new_post()`: read `form.video_token.data`; before validating, if a token is present and `promote()` can resolve it, treat the body as optional; on success set `Post(video_filename=...)`. Publish with neither text nor a valid token still fails with the existing "Write something before you publish." error.
      Updated validation shape in forms:
      ```python
      class NewPostForm(FlaskForm):
          body = TextAreaField(_l("Post text"), validators=[Optional(), Length(max=140, ...)])
          video_token = HiddenField()
          def validate(self, extra_validators=None):
              ok = super().validate(extra_validators)
              if ok and not (self.body.data or "").strip() and not self.video_token.data:
                  self.body.errors.append(_("Write something before you publish.")); return False
              return ok
      ```
      Stored body for video-only posts is `""` (column is NOT NULL, so empty string, not NULL). Language detection is skipped for empty text.
    files:
      - app/main/routes.py
      - app/main/forms.py
    rationale: Extends the text story's Publish rule (text OR finished video) while keeping the 140-char limit and error copy; the token is the only thing the form carries, so a half-uploaded file can never be published.
  - description: |
      Template + JS (app/templates/new_post.html), following the approved prototype's New post screen (states default / uploading / uploaded):
      - Video card (`.card.stack-sm`) after the text field, label "Video (optional)", containing a `.dropzone` (dashed `--border-width-strong`, `--color-border-strong`, `--radius-md`, `--color-bg-subtle`, `--space-4` padding) with a "Choose video file" `.btn.btn-secondary` that opens a hidden `<input type="file" accept="video/mp4,video/quicktime,.mp4,.mov">`, and the limit line `.text-muted.text-sm` rendered server-side from `config.VIDEO_MAX_BYTES` ("MP4 or MOV, up to 500 MB. One video per post.") so it is visible on first paint, before any upload (AC 2).
      - Uploading state: `.file-row` (`.thumb` 64px = `--size-avatar-lg`, file name + size, `role="status"` "Uploading 60%"), native `<progress class="progress-bar" max="100">` with aria-label "Video upload progress", hint "Keep this page open until the upload finishes."; "Cancel upload" `.btn.btn-secondary` is added next to Publish; Publish stays disabled with `aria-describedby` hint "Publish turns on when the video has finished uploading." (AC 3, 4).
      - Uploaded state: same row with "Uploaded", progress value 100; Publish enabled whether or not text is present (AC 5, 6); label becomes "Post text (optional with a video)".
      - Cancel upload: `xhr.abort()`, DELETE the pending token if any, clear the file input and hidden `video_token`, return to the default state: Choose video control shown again, text area untouched (AC 8, 9, 10).
      - Publish disable rule in JS: `publish.disabled = uploading || (!hasText && !uploaded)`.
      - One video per post: choosing is impossible while a video is attached/uploading (dropzone hidden).
      Server-rendered re-display (validation failure with a token) must also show the Uploaded state with the token kept. Strings via `_()`; sentence case, verbs on buttons.
    files:
      - app/templates/new_post.html
      - app/static/new_post.css
    rationale: |
      new_post.css already holds `.page-head` and `.form-actions`; add the prototype's page-local `.dropzone`, `.file-row`, `.thumb`, `.progress-bar` rules there, using only tokens (`--space-*`, `--radius-md`, `--color-bg-subtle`, `--color-border`, `--color-border-strong`, `--color-fg-muted`, `--border-width`, `--border-width-strong`, `--size-avatar-lg`). base.html already loads design-system/tokens.css (line 16) and prototype-utils.css (line 17); `.card`, `.stack-sm`, `.btn-*`, `.field-hint`, `.alert` are defined there. `.text-success` (used by the prototype's "Uploaded") is NOT defined in prototype-utils.css (grepped), so define it in new_post.css as `color: var(--color-success)`.
  - description: |
      Show a published video: in `_post.html` (Home/Explore/profile) and `post.html` render `{% if post.video_filename %}<video controls preload="metadata" class="post-video" src="{{ url_for('main.post_video', filename=post.video_filename) }}"></video>{% endif %}`, plus a `@bp.route("/media/video/<filename>")` (`post_video`, `@login_required`, regex-validated filename, `send_from_directory`, conditional/range support on). Add `.post-video` (width 100%, `--radius-md`) in a new app/static/post_video.css linked from base.html next to toast.css (new_post.css and comments.css are not loaded on Home, and the design-system copies should not be edited).
    files:
      - app/templates/_post.html
      - app/templates/post.html
      - app/templates/base.html
      - app/static/post_video.css
      - app/main/routes.py
    rationale: AC 7 sends the member to Home; the design's Home shows the published video with the post, so a video post must actually render there.
  - description: |
      Document the new settings (`VIDEO_MAX_BYTES`, `VIDEO_UPLOAD_DIR`) in README.md, and add `uploads/` to .gitignore.
    files:
      - README.md
      - .gitignore
    rationale: ADR-0012 configuration documentation; keeps uploaded media out of git.
tests:
  - |
    New file test_video_upload.py (unittest, reuse `TestConfig`/`make_user` from test_comments; set `TestConfig.VIDEO_UPLOAD_DIR` to a `tempfile.mkdtemp()` per test). Run narrowly: `python3 -m unittest test_video_upload -v`.
    AC1 - choose video attaches it: POST a small MP4 to the upload endpoint, then publish with the token and assert the video is on the post.
    ```python
    r = self.client.post("/new_post/video", data={"video": (io.BytesIO(b"\x00" * 1024), "clip.mp4")},
                         content_type="multipart/form-data")
    self.assertEqual(r.status_code, 200)
    token = r.get_json()["token"]
    self.assertRegex(token, r"^[0-9a-f]{32}$")
    ```
    Also: `.txt` upload returns 400; signed-out upload returns 302; a token belonging to another user is not promoted.
  - |
    AC2 - limit shown before upload: GET /new_post with no video and assert the size limit and format copy are in the HTML and no upload has happened.
    ```python
    html = self.client.get("/new_post").get_data(as_text=True)
    self.assertIn("up to 500 MB", html)
    self.assertIn("Choose video file", html)
    self.assertEqual(os.listdir(pending_dir), [])
    ```
    Plus: an upload larger than `VIDEO_MAX_BYTES` (set to 1024 in the test config) returns 413 JSON.
  - |
    AC3 - progress is shown: the page ships a `<progress ... max="100">` element, a `role="status"` percent label and the progress-reporting script. Assert markup and hooks.
    ```python
    self.assertRegex(html, r'<progress[^>]*max="100"')
    self.assertIn("upload.onprogress", html)
    ```
    Real progress animation is verified manually (unittest has no browser); the manual check goes in the PR description.
  - |
    AC4 - Publish disabled while uploading with text: assert the page's publish-sync rule and the disabled hint.
    ```python
    self.assertIn("publish.disabled = uploading ||", html)
    self.assertIn("Publish turns on when the video has finished uploading.", html)
    ```
    Server side: POST /new_post with text and a `video_token` that is not a finished upload (unknown token) does not create a video post - text-only fallback is rejected with the same error path as an invalid token (assert `post_count()` unchanged, response shows the error).
  - |
    AC5 - finished video, empty text, Publish enabled: render /new_post with a valid `video_token` in the form (validation-redisplay) and assert Publish has no `disabled` attribute.
    ```python
    self.assertNotRegex(html, r'<button[^>]*id="publish"[^>]*\bdisabled\b')
    ```
  - |
    AC6 - finished video plus text, Publish enabled: same render with `body="Our weekend hike."`; and publishing creates a Post with both.
    ```python
    p = db.session.scalar(sa.select(Post))
    self.assertEqual(p.body, "Our weekend hike.")
    self.assertTrue(p.video_filename.endswith(".mp4"))
    ```
  - |
    AC7 - video-only publish goes to Home:
    ```python
    r = self.client.post("/new_post", data={"body": "", "video_token": token})
    self.assertEqual(r.status_code, 302)
    self.assertTrue(r.headers["Location"].endswith("/index") or r.headers["Location"] == "/")
    p = db.session.scalar(sa.select(Post)); self.assertEqual(p.body, "")
    ```
    Also: neither text nor token still returns 200 with "Write something before you publish." and creates no post; Home (`GET /`) for a following user contains a `<video` tag for that post; the pending file no longer exists and the final file does.
  - |
    AC8 - Cancel upload attaches no video: after uploading, `DELETE /new_post/video/<token>` returns 204, the pending file is gone, and publishing with that token yields no video.
    ```python
    self.assertEqual(self.client.delete(f"/new_post/video/{token}").status_code, 204)
    self.assertEqual(os.listdir(pending_dir), [])
    r = self.client.post("/new_post", data={"body": "hi", "video_token": token})
    self.assertIsNone(db.session.scalar(sa.select(Post)).video_filename)
    ```
    Plus: the page ships a "Cancel upload" button wired to `xhr.abort()` (assert string present).
  - |
    AC9 - text kept on cancel: the Cancel handler never touches the textarea. Assert the script contains no write to `box.value` in the cancel path (string check on the cancel function body) and verify manually in a browser; server side, a text-only POST after a discarded token publishes the typed text.
  - |
    AC10 - Choose video shown again: assert the Choose video control and dropzone are in the default markup and that the cancel handler un-hides it (`dropzone.hidden = false`); manual browser check recorded in the PR.
  - |
    Existing-data test (migration adds a nullable column): create a Post without a video and assert it still loads and renders on Home.
    ```python
    p = Post(body="old", author=self.user); db.session.add(p); db.session.commit()
    self.assertIsNone(db.session.get(Post, p.id).video_filename)
    self.assertEqual(self.client.get("/explore").status_code, 200)
    ```
    Regression: `python3 -m unittest test_new_post test_comments tests -v` must still pass (existing test_new_post assertions about Publish disabled with empty text must stay green).
assumptions_or_open_questions:
  - |
    Deferred question "direct to storage or through the app server; can an interrupted upload resume?" - answered for this story: through the app server (XHR to a Flask endpoint) so progress events work with the existing stack and no new infrastructure; resume is NOT supported (a dropped upload is a failure, owned by STORY-015). A human should confirm, because ADR-0008 targets AWS ECS/Fargate whose containers have ephemeral disk, so production needs durable storage (S3 or a mounted volume) behind `videos.py` before real use.
  - |
    Project-wide open question on retention and cleanup of abandoned or cancelled uploads is NOT decided. This plan only deletes a pending file on Cancel upload. Abandoned pending files (tab closed) are never reaped here; a cleanup job (RQ per ADR-0004) and a retention period need a product decision and a follow-up story.
  - |
    Design vs. scope conflict: the prototype's limit text says "up to 5 minutes", but no acceptance criterion or stack component can verify duration (no ffprobe/transcoding in the stack). The plan shows format and size only and does not enforce duration; confirm whether the duration limit should be dropped from the design or added as a later story.
  - |
    The prototype's "Cancel" and "Publish" are unchanged from STORY-013 (Cancel links to Home). The prototype's Drag-and-drop text ("Drag a video here, or") is not in any AC; drag-and-drop handling is planned as a small enhancement on the same dropzone only if trivial, otherwise the copy is shortened to "Choose a video" - reviewer to confirm.
  - |
    "Common formats" is taken as MP4 and MOV (from the prototype's limit text), validated by extension and browser MIME type only; no content sniffing. 500 MB is taken from the prototype as the size limit.
  - |
    The 140-character post limit and the Home feed pagination are unchanged. Video-only posts store body as an empty string because Post.body is NOT NULL.
  - |
    The browser-side behaviours (progress, cancel, enabling Publish) cannot be exercised by unittest; they are covered by markup/hook assertions plus a manual browser check. Adding a JS test runner is out of scope (not in the confirmed stack).
estimated_points: 5
package_dependencies: []
notes: |
  ### Data & rollout
  - **Existing data**: one Alembic migration adds a NULLABLE `post.video_filename` column; existing rows get NULL and remain readable (text-only). No constraint or NOT NULL change.
  - **Backfill / seed**: none needed.
  - **Settings**: `VIDEO_MAX_BYTES` (default 524288000), `VIDEO_UPLOAD_DIR` (default `<repo>/uploads`), `MAX_CONTENT_LENGTH` derived from the first; all safe when unset; documented in README.md and defined in config.py.
  - **Provisioning**: the upload directory must be writable by the app (created on demand by `videos.py`); in production it must be durable and shared by web instances (see open question on storage). Nginx (deployment/nginx/microblog) `client_max_body_size` must allow ~501 MB or uploads fail at the proxy.
  - **Order and rollback**: run `flask db upgrade` before deploying the new code (code reads the column). Rollback: `flask db downgrade` drops the column; uploaded files stay on disk and are harmless.

  ### Design source
  Read the approved prototype's "New post" screen: states default (Video card with dashed dropzone, Choose video file, limit line, Publish disabled), uploading (file-row with thumb, "Uploading 60%", native progress, Cancel upload, disabled Publish plus hint) and uploaded (Uploaded label, progress 100, Publish enabled, text optional). The error and posted states belong to STORY-015 and STORY-013 and are not built here. Tokens are loaded in base.html lines 16-17 from app/static/design-system/. The prototype's `.dropzone`, `.file-row`, `.thumb`, `.video-frame`, `.progress-bar` are page-local inline styles there, so they are re-defined in app/static/new_post.css on the same tokens.

  ```mermaid
  flowchart TD
    T[new_post.html + new_post.css<br/>Video card, XHR upload, Cancel] -->|POST file / DELETE token| R[main/routes.py<br/>upload_video, discard_video, new_post]
    T -->|form with video_token| R
    R --> V[main/videos.py<br/>save_pending, delete_pending, promote]
    R --> F[main/forms.py<br/>NewPostForm optional body + video_token]
    R --> M[models.py Post.video_filename]
    M --> G[migrations: post_video]
    R --> H[_post.html / post.html<br/>render video]
    C[config.py<br/>VIDEO_MAX_BYTES, VIDEO_UPLOAD_DIR] --> R
    classDef touched fill:#f96,color:#000
    class T,R,V,F,M,G,H,C touched
  ```
review_focus: |
  IN: one video per post via app-server upload with progress, Cancel upload, size limit shown up front, and Publish allowed with text, video, or both. OUT: failure/retry handling and resume (STORY-015), transcoding, duration enforcement, retention/cleanup of abandoned uploads (open question). Riskiest parts are the token handling in videos.py (path traversal, cross-user tokens), the changed NewPostForm validation that must keep the text story's rules and error copy, and storage durability on Fargate; the empty-string body for video-only posts and the missing `.text-success` definition being added locally are deliberate.
