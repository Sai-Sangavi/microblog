summary: |
  Add a dedicated "New post" page to the Flask app so a signed-in member can write and publish a text post. A new `main.new_post` route (`/new_post`, GET+POST, `@login_required`) renders a labelled, placeholdered, initially empty textarea with Publish disabled until the text has non-whitespace content (live via a small inline script, and re-enforced server-side), a Cancel link to Home, and on success saves a `Post`, flashes a "Posted" toast and redirects to Home (the existing `following_posts()` ordering already puts the member's own new post first). On a save failure the route rolls back and re-renders the same page with the text preserved and a danger alert. `base.html` gets a "New post" nav entry for signed-in members and renders a `toast`-category flash as a `.toast` that auto-dismisses after 3 seconds. Video upload is explicitly out of scope (separate stories).
scope:
  - description: |
      Add `NewPostForm` (a `FlaskForm` with one `TextAreaField` named `body`, label "Post text", `DataRequired` plus `Length(max=140)` because `Post.body` is `String(140)`). Whitespace-only input must fail `DataRequired` (WTForms strips for that check) so AC 10 is enforced server-side too.

      ```python
      class NewPostForm(FlaskForm):
          body = TextAreaField(
              _l("Post text"),
              validators=[
                  DataRequired(message=_l("Write something before you publish.")),
                  Length(max=140, message=_l("Shorten your post to 140 characters to publish.")),
              ],
          )
          submit = SubmitField(_l("Publish"))
      ```
    files:
      - app/main/forms.py
    rationale: |
      Mirrors the existing `CommentForm` pattern in the same file (custom messages, `_l` labels). The existing `PostForm` is left alone because Home still uses it.
  - description: |
      Add the route in `app/main/routes.py`, plus a tiny private helper shared with `index()` for language detection (no behaviour change to `index`).

      ```python
      @bp.route("/new_post", methods=["GET", "POST"])
      @login_required
      def new_post():
          form = NewPostForm()
          publish_error = False
          if form.validate_on_submit():
              try:
                  post = Post(body=form.body.data.strip(), author=current_user,
                              language=_detect_language(form.body.data))
                  db.session.add(post)
                  db.session.commit()
              except SQLAlchemyError:
                  db.session.rollback()
                  publish_error = True
              else:
                  flash(_("Posted"), "toast")
                  return redirect(url_for("main.index"))
          return render_template("new_post.html", title=_("New post"), form=form,
                                 publish_error=publish_error)
      ```

      Failure path returns HTTP 200 with the form re-bound to the submitted data, so the text stays in the textarea (AC 13). `from sqlalchemy.exc import SQLAlchemyError` is a new import (SQLAlchemy is already a dependency).
    files:
      - app/main/routes.py
    rationale: |
      Follows the existing route style (`@bp.route` + `@login_required` + `flash` + `redirect`). Home's `index()` already orders `following_posts()` by timestamp descending and includes the member's own posts, so AC 11 needs no Home query change.
  - description: |
      Create `app/templates/new_post.html` extending `base.html`, built from the approved prototype's "New post" screen (default and error states): `.stack-lg` wrapper; `.page-head` with `<h1>` "New post"; a `<form method="post" novalidate>` with `form.hidden_tag()`; a `.field` containing `<label for="post-text">` (visible), a `.textarea` (rows=5, `placeholder="What is on your mind?"`, `aria-describedby` to the `.field-hint` "Publish turns on once you have written something."), `.field-error` per error with `.is-invalid` and `aria-invalid` on the textarea; when `publish_error`, a leading `.alert.alert-danger[role=alert]` ("Your post didn't publish. Check your connection and press Publish to try again. Your text is still here.") and the textarea `aria-describedby` points at it; `.form-actions` with Cancel (`<a class="btn btn-secondary" href="{{ url_for('main.index') }}">`) then Publish (`<button class="btn btn-primary" type="submit" id="publish">`, rendered `disabled` when the text is empty/whitespace). A small inline script toggles `publish.disabled = box.value.trim().length === 0` on `input` and once on load (same logic as the prototype's `sync()`). The textarea is rendered empty on GET so the placeholder is not text (AC 4).

      Prototype elements deliberately NOT built: the "Video (optional)" card, "Posting to Microblog" line (decoration), uploading/video-failed states and the "Remove video"/"Publish without video" buttons (STORY-014/015), and the prototype's in-page "Your post is live" state (the story redirects to Home instead).
    files:
      - app/templates/new_post.html
    rationale: |
      Matches the design's New post layout. Uses only classes already defined in `app/static/design-system/prototype-utils.css` (`.stack-lg`, `.field`, `.field-hint`, `.field-error`, `.textarea`, `.is-invalid`, `.btn`, `.btn-primary`, `.btn-secondary`, `.alert`, `.alert-danger`), which `base.html` already loads at lines 16-17.
  - description: |
      Create `app/static/new_post.css` for the prototype-only layout classes that `prototype-utils.css` does not define (verified: `.page-head` and `.form-actions` are only in the prototype's inline style). Copy them with the same token references:

      ```css
      .page-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--space-2); }
      .page-head h1 { margin: 0; font-size: var(--font-size-xl); line-height: var(--line-height-tight); }
      .form-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: var(--space-2); }
      ```

      Load it from `new_post.html` via `{% block styles %}` (same way `post.html` loads `comments.css`). Also create `app/static/toast.css` for the toast host (`.toast-host`: fixed, centred, `bottom`, `padding: 0 var(--space-3)`, `z-index: var(--z-toast)`, `pointer-events: none`; `.toast-host .toast { pointer-events: auto; max-width: var(--size-toast); }`), linked from `base.html` because the toast shows on Home. `.toast` and `.toast.is-open` themselves are already in `prototype-utils.css` (line ~202-207). The prototype's `bottom: 56px` is a raw value for its reviewer bar; use `bottom: var(--space-3)` instead (no raw px).
    files:
      - app/static/new_post.css
      - app/static/toast.css
    rationale: |
      Tokens are already loaded app-wide (`base.html` links `design-system/tokens.css` and `prototype-utils.css`), so no new token import is needed. Only tokens are used, no colour literals.
  - description: |
      Edit `app/templates/base.html`: (1) add a "New post" nav link (`url_for('main.new_post')`, label `_('New post')`) inside the signed-in branch (`{% else %}` of `current_user.is_anonymous`), before Messages, so it is absent for signed-out visitors; (2) split flashes by category: `get_flashed_messages(with_categories=True)` renders category `toast` as `<div class="toast-host"><div class="toast is-open" role="status" aria-live="polite" id="posted-toast" data-dismiss-ms="3000">{{ message }}</div></div>` and every other category as the existing `.alert alert-info`; (3) add a script that, for `#posted-toast`, does `setTimeout(() => toast.classList.remove('is-open'), 3000)` (reads `data-dismiss-ms`); (4) link `toast.css`.
    files:
      - app/templates/base.html
    rationale: |
      The nav entry satisfies AC 1 in the real nav, which lives only in `base.html`. Flash categories keep existing flashed messages (comment posted, profile saved, etc.) rendering exactly as before.
  - description: |
      Add Spanish translation entries for the new strings ("New post", "Posted", "Post text", "Publish", the validation and error messages) to `app/translations/es/LC_MESSAGES/messages.po` if that file lists existing UI strings (ADR-0014 localization; the guidelines say every string is translated). Skip `.mo` compilation unless the repo already commits compiled catalogs.
    files:
      - app/translations/es/LC_MESSAGES/messages.po
    rationale: |
      Keeps the new copy translatable; existing routes use `_()` for all strings.
tests:
  - |
    New file `test_new_post.py` (same harness as `test_comments.py`: `TestConfig` with `sqlite://`, `WTF_CSRF_ENABLED = False`, `make_user`, log in via `POST /auth/login`). Run narrowly with `python3 -m unittest test_new_post -v`. AC 1 — written first, fails with 404 today:
    ```python
    def test_nav_has_new_post_entry_and_page_loads(self):
        home = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/new_post"', home)
        r = self.client.get("/new_post")
        self.assertEqual(r.status_code, 200)
        self.assertIn("<h1", r.get_data(as_text=True))
    def test_signed_out_has_no_new_post_entry_and_is_redirected(self):
        anon = self.app.test_client()
        self.assertNotIn('href="/new_post"', anon.get("/explore", follow_redirects=True).get_data(as_text=True))
        self.assertEqual(anon.get("/new_post").status_code, 302)
    ```
  - |
    AC 2 and 3 — label and placeholder:
    ```python
    def test_text_field_has_label_and_placeholder(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r'<label for="body"[^>]*>\s*Post text\s*</label>')
        self.assertIn('placeholder="What is on your mind?"', html)
    ```
  - |
    AC 4 — field is empty, placeholder not entered as text:
    ```python
    def test_text_field_is_empty_on_open(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r'<textarea[^>]*id="body"[^>]*>\s*</textarea>')
        self.assertNotRegex(html, r'<textarea[^>]*>[^<]*What is on your mind')
    ```
  - |
    AC 5 — Publish disabled when empty (server-rendered state; the live toggle is the same expression in the inline script):
    ```python
    def test_publish_disabled_when_empty(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r'<button[^>]*id="publish"[^>]*\bdisabled\b')
    ```
  - |
    AC 6 — Publish enabled with non-empty text (re-render after a failed save carries text, so the button must not be disabled):
    ```python
    def test_publish_enabled_when_text_present(self):
        with patch.object(db.session, "add", side_effect=SQLAlchemyError):
            html = self.client.post("/new_post", data={"body": "hi"}).get_data(as_text=True)
        self.assertNotRegex(html, r'<button[^>]*id="publish"[^>]*\bdisabled\b')
        self.assertIn("document.getElementById", html)  # live toggle script present
    ```
  - |
    AC 7 — publishing redirects to Home and saves the post:
    ```python
    def test_publish_redirects_home(self):
        r = self.client.post("/new_post", data={"body": "Hello there"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/index") or r.headers["Location"] == "/")
        self.assertEqual(db.session.scalar(sa.select(sa.func.count(Post.id)).where(Post.body == "Hello there")), 1)
    ```
  - |
    AC 8 — "Posted" toast on Home after publishing, and only then:
    ```python
    def test_posted_toast_shown_on_home(self):
        html = self.client.post("/new_post", data={"body": "Hello there"}, follow_redirects=True).get_data(as_text=True)
        self.assertRegex(html, r'class="toast is-open"[^>]*>\s*Posted\s*<')
        again = self.client.get("/").get_data(as_text=True)
        self.assertNotIn('id="posted-toast"', again)
    ```
  - |
    AC 9 — Cancel goes to Home without saving:
    ```python
    def test_cancel_links_to_home_and_saves_nothing(self):
        html = self.client.get("/new_post").get_data(as_text=True)
        self.assertRegex(html, r'<a[^>]*class="btn btn-secondary"[^>]*href="/"?[^"]*"[^>]*>\s*Cancel')
        self.assertEqual(db.session.scalar(sa.select(sa.func.count(Post.id))), 0)
    ```
  - |
    AC 10 — only spaces or line breaks: Publish disabled on render, and the server refuses to create a post:
    ```python
    def test_whitespace_only_is_rejected(self):
        r = self.client.post("/new_post", data={"body": "  \r\n \n "})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Write something before you publish.", r.get_data(as_text=True))
        self.assertEqual(db.session.scalar(sa.select(sa.func.count(Post.id))), 0)
    ```
  - |
    AC 11 — the new post is first in the Home feed immediately (a followed/own older post exists):
    ```python
    def test_new_post_is_first_on_home(self):
        db.session.add(Post(body="older post", author=self.user, timestamp=datetime.now(timezone.utc) - timedelta(hours=1)))
        db.session.commit()
        html = self.client.post("/new_post", data={"body": "brand new"}, follow_redirects=True).get_data(as_text=True)
        self.assertLess(html.index("brand new"), html.index("older post"))
    ```
  - |
    AC 12, 13, 14 — save failure keeps the member on the page, keeps text, shows an error (one `patch.object(db.session, "add", side_effect=SQLAlchemyError)` makes the save fail; `before_request`'s commit is not affected because it never calls `add`):
    ```python
    def test_publish_failure_keeps_page_text_and_shows_error(self):
        with patch.object(db.session, "add", side_effect=SQLAlchemyError):
            r = self.client.post("/new_post", data={"body": "keep me"})
        html = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)                                  # AC 12: no redirect
        self.assertRegex(html, r'<textarea[^>]*>\s*keep me\s*</textarea>')      # AC 13
        self.assertRegex(html, r'class="alert alert-danger"[^>]*role="alert"')  # AC 14
        self.assertIn("Your post didn't publish", html)
        self.assertEqual(db.session.scalar(sa.select(sa.func.count(Post.id))), 0)
    ```
  - |
    AC 15 — toast auto-dismisses after about 3 seconds. The Flask test client cannot run JS, so assert the contract the script reads and the script's timer; verify the real behaviour manually in a browser (open Home after publishing, toast gone after ~3 s):
    ```python
    def test_toast_declares_three_second_dismissal(self):
        html = self.client.post("/new_post", data={"body": "Hello"}, follow_redirects=True).get_data(as_text=True)
        self.assertIn('data-dismiss-ms="3000"', html)
        self.assertIn("setTimeout", html)
    ```
  - |
    Regression guard: other flashed messages still render as `.alert-info` (existing `test_comments.py` suite must stay green):
    ```python
    def test_non_toast_flash_still_renders_as_alert(self):
        html = self.client.post(f"/post/{self.post.id}", data={"body": "Nice"}, follow_redirects=True).get_data(as_text=True)
        self.assertIn('class="alert alert-info"', html)
        self.assertNotIn('id="posted-toast"', html)
    ```
assumptions_or_open_questions:
  - |
    The prototype has no New post entry in its shell (its own design note says Home carries a "New post" button as a stand-in), and the UI guidelines list exactly five destinations. The AC requires a nav entry, so the plan adds "New post" to the signed-in nav in `base.html` between Explore and Messages. Reviewer to confirm placement, and that the UI-guidelines nav list should be updated by the design-system owner.
  - |
    The production nav is Bootstrap navbar markup in `base.html`, not the design-system shell the prototype draws. The plan keeps the existing nav and styles only the new page and toast with design tokens; migrating the whole shell is out of scope.
  - |
    `Post.body` is `String(140)` (app/models.py line 302) and the existing `PostForm` enforces 140. The plan enforces the same limit on New post with a field error; the prototype shows no character counter. Confirm 140 is the intended limit (the guidelines mention a character hint in `.field-hint`; none is built because the story and design don't ask for one).
  - |
    Home still carries the old inline post form from `index()`/`index.html`. The story does not say to remove it, so it is left unchanged (removing it would be a separate behaviour change). Confirm whether it should go now that posting has its own page.
  - |
    A failed publish is treated as a database save error (caught `SQLAlchemyError`, rollback, re-render at HTTP 200 with a danger alert). The prototype's copy mentions connection, but this is a server-rendered form so there is no client network call to fail separately.
  - |
    Toast auto-dismiss is client-side JS (3000 ms) and is unit-tested only through its markup contract; the timing itself needs a manual browser check.
  - |
    The project-wide open question about video retention and cleanup of abandoned uploads is not addressed here: this story is text-only and stores no video. It stays open for the video stories.
  - |
    The `.mo` catalog and Spanish `.po` updates are best-effort. If translations are not maintained per story in this repo, drop that scope item.
estimated_points: 3
package_dependencies: []
notes: |
  ### Data & rollout

  None — no schema change, migration, backfill, new setting or provisioning. The route writes ordinary `Post` rows (same table, columns and `body` limit that `index()` already uses), so existing rows are untouched. Safe to deploy in one step; rollback is reverting the code (posts already created remain valid posts).

  ### Design and tokens

  - Read the approved prototype: New post screen (h1 "New post"; `.field` with visible label "Post text", `.textarea` with placeholder "What is on your mind?", `.field-hint`; `.form-actions` right-aligned Cancel `.btn-secondary` + Publish `.btn-primary`, disabled while empty; error state with `.alert-danger`, `.textarea.is-invalid`, text kept) and the Home screen (`.toast` "Posted", shown for 3 s; new post inserted at top).
  - Tokens load today via `app/templates/base.html` lines 16-17 (`design-system/tokens.css`, `design-system/prototype-utils.css`, served from `app/static/design-system/`). Nothing new to import.
  - Tokens used by the new CSS: `--space-2`, `--space-3`, `--font-size-xl`, `--line-height-tight`, `--z-toast`, `--size-toast`. No colour literals or raw pixels.
  - Conflict between prototype and ACs: the prototype includes a "Video (optional)" card and a post-publish "Your post is live" in-page state; the story says video is a separate story and AC 7 says publish goes to Home. The plan follows the ACs.

  ### Shape of the change

  ```mermaid
  flowchart TD
    nav["base.html nav + flash/toast rendering"]:::touched
    routes["app/main/routes.py new_post()"]:::touched
    forms["app/main/forms.py NewPostForm"]:::touched
    tpl["templates/new_post.html"]:::touched
    css["static/new_post.css + toast.css"]:::touched
    index["routes.index() Home feed"]
    model["models.Post / following_posts()"]
    ds["design-system tokens.css + prototype-utils.css"]
    nav -->|"New post link"| routes
    routes -->|"validates with"| forms
    routes -->|"renders"| tpl
    tpl -->|"styled by"| css
    css --> ds
    routes -->|"flash Posted toast, redirect"| index
    routes -->|"saves"| model
    index -->|"reads own post first"| model
    index -->|"extends"| nav
    classDef touched fill:#f96,color:#000
  ```
review_focus: |
  IN scope: the `/new_post` page, nav entry, Publish enable/disable (client live + server enforced), Cancel, redirect to Home with a 3 s "Posted" toast, and failure handling that keeps the text. OUT: video upload, draft-protection confirmation, removing Home's existing inline post form, migrating the shell to the design-system shell. Riskiest part is the `base.html` flash change (category-based toast vs alert) — check existing flashed messages still render as alerts — and the failure test that patches `db.session.add` so `before_request`'s commit is not broken. The 140-char limit and the failure being a caught `SQLAlchemyError` are deliberate (match `Post.body`; server-rendered form).
