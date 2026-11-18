summary: |
  Add a public post page (`/post/<id>`) that shows the post, a flat oldest-first list of its comments, and, for signed-in users only, a comment form (max 1000 characters, empty rejected). Signed-out visitors see the same page with a "Log in to comment" link to the sign-in page instead of the form, and a "No comments yet" empty state when there are none. This needs a new `Comment` model plus an Alembic migration, a `CommentForm`, one new route, two templates (post page and a comment partial), a small stylesheet built on the existing design tokens, and a link from each post in the feed to its post page so the page is reachable. Built test-first with `unittest` in a new `test_comments.py`, following the pattern of `test_environments.py`.
scope:
  - description: |
      Add a `Comment` model in `app/models.py`, after `Post`, mirroring the `Post`/`Message` style (SQLAlchemy 2 `Mapped` columns, `timestamp` default `datetime.now(timezone.utc)`, indexed FKs).

      ```python
      class Comment(db.Model):
          id: so.Mapped[int] = so.mapped_column(primary_key=True)
          body: so.Mapped[str] = so.mapped_column(sa.String(1000))
          timestamp: so.Mapped[datetime] = so.mapped_column(
              index=True, default=lambda: datetime.now(timezone.utc))
          post_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Post.id), index=True)
          user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
          post: so.Mapped[Post] = so.relationship(back_populates="comments")
          author: so.Mapped[User] = so.relationship(back_populates="comments")
      ```

      Add `comments: so.WriteOnlyMapped['Comment'] = so.relationship(back_populates='post')` on `Post` and the same on `User`. Use WriteOnlyMapped like the other collections, and read with `post.comments.select().order_by(Comment.timestamp.asc(), Comment.id.asc())`. The `id` tiebreaker keeps same-timestamp comments stable.
    files:
      - app/models.py
    rationale: |
      Comments are new stored data tied to a post and an author. A flat list needs no parent_id, which also enforces the "no replies" scope.
  - description: |
      Alembic migration creating the `comment` table and its three indexes (`ix_comment_timestamp`, `ix_comment_post_id`, `ix_comment_user_id`). Set `down_revision = "a1c2e3f4b5d6"` (the current head, the environments migration). Follow the `batch_alter_table` index style used there. `downgrade()` drops the indexes and the table.
    files:
      - migrations/versions/b2d4f6a8c0e1_comments.py
    rationale: |
      PostgreSQL in production, so the schema must be migrated; `db.create_all()` in tests does not cover it.
  - description: |
      Add `CommentForm` in `app/main/forms.py`, next to `MessageForm`.

      ```python
      class CommentForm(FlaskForm):
          body = TextAreaField(_l('Add a comment'), validators=[
              DataRequired(), Length(min=1, max=1000)])
          submit = SubmitField(_l('Post comment'))
      ```

      `DataRequired` rejects empty and whitespace-only text; `Length(max=1000)` accepts exactly 1000 and rejects 1001. Button text is "Post comment" per the prototype (a verb, not "Submit").
    files:
      - app/main/forms.py
    rationale: |
      Server-side validation of AC 7, 8, 9. The browser must not be the only guard.
  - description: |
      Add the route in `app/main/routes.py` (import `Comment` and `CommentForm`).

      ```python
      @bp.route('/post/<int:id>', methods=['GET', 'POST'])
      def post(id):
          post = db.get_or_404(Post, id)
          form = CommentForm()
          if form.validate_on_submit():
              if not current_user.is_authenticated:
                  return current_app.login_manager.unauthorized()
              db.session.add(Comment(body=form.body.data, post=post, author=current_user))
              db.session.commit()
              flash(_('Your comment is posted'))
              return redirect(url_for('main.post', id=post.id) + '#comments')
          comments = db.session.scalars(post.comments.select().order_by(
              Comment.timestamp.asc(), Comment.id.asc())).all()
          return render_template('post.html', title=_('Post'), post=post,
                                 form=form, comments=comments)
      ```

      The route is deliberately NOT `@login_required`: every other route in this file is, but AC 2, 4 and 10-11 require signed-out visitors to read the page. The POST branch checks authentication itself and sends a signed-out poster to the login page. A failed validation re-renders the page with status 200, keeping the text and showing the error. Redirect after a successful POST so a refresh does not repost. `before_app_request` already sets `g.locale` for anonymous users.
    files:
      - app/main/routes.py
    rationale: |
      The one new endpoint covering AC 1-13. There is no post detail page today, so this creates it.
  - description: |
      Add `app/templates/post.html` (extends `base.html`) and a partial `app/templates/_comment.html`, built from the prototype's "Post" screen (`.post-page stack-lg`):

      1. Post card, `.card` with a `.cluster` row: `.avatar` with the author's initials, author link to `main.user`, `.text-muted .text-sm` timestamp via `moment(post.timestamp).fromNow()`, then the body in `.post-body`.
      2. `<section aria-label="Comments" class="stack-lg" id="comments">` with `<h2 class="text-lg">` reading `Comments ({{ comments|length }})`.
      3. If `current_user.is_authenticated`: a `.card .stack` form with `form.hidden_tag()` (CSRF), a `.field` holding the label, a `.textarea` (class `is-invalid` and `aria-invalid="true"` when `form.body.errors`), a `.field-error role="alert"` with the error text, and `.form-foot` holding a `.field-hint` "0 / 1000" counter and the single `.btn .btn-primary` "Post comment". Else: `<div class="prompt"><a href="{{ url_for('auth.login', next=request.path) }}">Log in to comment</a></div>`, with no form element at all.
      4. If there are no comments: `.empty-state` with `<p class="text-bold">No comments yet</p>` and the muted line "Be the first to say something about this post." Otherwise `<ol class="comment-list">` of `_comment.html` rows (`li.comment` with `.comment-head`: `.avatar-sm .avatar` initials, `<strong>` author name, `.text-muted .text-sm` timestamp; then `<p>` with the body). Autoescaped, never `|safe`.

      Add a small inline script, as in the prototype, that updates the "n / 1000" counter on input. The server stays the source of truth, so the page works without JS. Error copy for an invalid submit: "Write something before you post." for empty and "This comment is too long. Shorten it to 1000 characters to post." for over-limit, set through custom messages on the validators so they say what to do next.

      Prototype states left out on purpose: the like buttons (the prototype's own note says they are not in scope), the collapsed/liked/expanded toggle (AC 4 requires the comments to be listed on the post, so the section is always expanded), and the "Posting…" disabled state (submit is a normal form post).
    files:
      - app/templates/post.html
      - app/templates/_comment.html
    rationale: |
      UI for AC 1-6 and 10-13, matching the approved prototype: comments are plain `.divider`-style rows rather than cards so they read as one flat list.
  - description: |
      Styling. `base.html` already loads `design-system/tokens.css` and `design-system/prototype-utils.css` (lines 16-17), and `prototype-utils.css` already defines `.card`, `.avatar`, `.avatar-sm`, `.empty-state`, `.field-error`, `.textarea`, `.btn-primary` and `.divider`. I did not re-check every other class (`.stack`, `.stack-lg`, `.cluster`, `.field`, `.field-hint`, `.text-muted`, `.text-sm`, `.text-lg`, `.text-bold`, `.is-invalid`); the implementer must grep `prototype-utils.css` and add any that are missing on the same tokens.

      The prototype's own inline rules (`.post-page`, `.post-body`, `.comment-list`, `.comment`, `.comment:first-child`, `.comment-head`, `.comment p`, `.form-foot`, `.prompt`, `.prompt a`) are not in the design system. Define them in a new `app/static/comments.css` using only tokens: `--size-container`, `--space-1`, `--space-2`, `--space-3`, `--border-width`, `--color-border`, `--color-bg-subtle`, `--radius-lg`, `--font-weight-medium`, `--size-control`. Examples are `.comment { padding: var(--space-3) 0; border-bottom: var(--border-width) solid var(--color-border); }` and `.comment p { white-space: pre-wrap; overflow-wrap: anywhere; }`. No hex/rgb literals and no raw px values. Add `{% block styles %}{% endblock %}` inside `<head>` in `base.html` and link the stylesheet from `post.html`.
    files:
      - app/static/comments.css
      - app/templates/base.html
    rationale: |
      Reuses the existing token pipeline instead of inventing styles. Keeps the 48rem single-column layout and the 44px (`--size-control`) touch target on the login link.
  - description: |
      Make the page reachable: in `app/templates/_post.html`, wrap the post timestamp (`moment(post.timestamp).fromNow()`) in a link to `url_for('main.post', id=post.id)` and add a "Comments" link under the body, shown for every post in feeds and search results. No other feed layout change.
    files:
      - app/templates/_post.html
    rationale: |
      Without an entry point the new page could not be opened from the app. This is the minimum wiring and is not a redesign of the post list.
tests:
  - |
    New file `test_comments.py` (picked up by `python3 -m unittest discover -s . -p 'test_*.py'`). Narrow run: `python3 -m unittest test_comments -v`. Setup mirrors `test_environments.py`: a `TestConfig(Config)` with `SQLALCHEMY_DATABASE_URI = "sqlite://"`, `ELASTICSEARCH_URL = None`, `WTF_CSRF_ENABLED = False`; `create_app`, `db.create_all()`, a user "susan" and a post; sign in with `self.client.post("/auth/login", data={"username": "susan", "password": "cat"})`. Helpers: `make_comment(post, user, body, ts)` and `page(post)` returning `self.client.get(f"/post/{post.id}").get_data(as_text=True)`. Write all tests first and watch them fail (no `Comment` model, no route).
  - |
    AC 1 `test_signed_in_comment_appears`:
    ```python
    r = self.client.post(url, data={"body": "Nice run"}, follow_redirects=True)
    self.assertEqual(r.status_code, 200)
    self.assertIn("Nice run", r.get_data(as_text=True))
    self.assertEqual(db.session.scalar(sa.select(sa.func.count(Comment.id))), 1)
    ```
  - |
    AC 2 `test_signed_out_has_no_form` (fresh client, not logged in):
    ```python
    html = anon.get(url).get_data(as_text=True)
    self.assertNotIn("<textarea", html)
    self.assertNotIn('name="body"', html)
    ```
  - |
    AC 3 `test_signed_in_sees_form`:
    ```python
    html = self.page(post)
    self.assertIn("<textarea", html)
    self.assertIn("Post comment", html)
    ```
  - |
    AC 4 `test_comments_are_listed` creates two comments and asserts both bodies are in the page. Also `test_post_page_404_for_unknown_post` asserts `self.client.get("/post/999").status_code == 404`.
  - |
    AC 5 `test_comments_are_one_flat_list`:
    ```python
    html = self.page(post)
    self.assertEqual(html.count('<ol class="comment-list"'), 1)
    self.assertEqual(html.count('class="comment"'), 3)
    ```
    Plus a model-level assertion that `Comment` has no `parent_id` column: `self.assertNotIn("parent_id", Comment.__table__.columns)`.
  - |
    AC 6 `test_comments_oldest_first` creates comments with explicit timestamps inserted out of order (newest first), then:
    ```python
    html = self.page(post)
    self.assertLess(html.index("first body"), html.index("second body"))
    self.assertLess(html.index("second body"), html.index("third body"))
    ```
    Also a same-timestamp case ordered by id.
  - |
    AC 7 `test_empty_comment_rejected` posts `body=""` and also `body="   "`:
    ```python
    r = self.client.post(url, data={"body": ""})
    self.assertEqual(r.status_code, 200)
    self.assertEqual(db.session.scalar(sa.select(sa.func.count(Comment.id))), 0)
    self.assertIn("Write something before you post.", r.get_data(as_text=True))
    ```
  - |
    AC 8 `test_comment_of_exactly_1000_chars_is_saved`:
    ```python
    body = "a" * 1000
    r = self.client.post(url, data={"body": body}, follow_redirects=True)
    self.assertIn(body, r.get_data(as_text=True))
    ```
  - |
    AC 9 `test_comment_of_1001_chars_is_rejected`:
    ```python
    r = self.client.post(url, data={"body": "a" * 1001})
    self.assertEqual(db.session.scalar(sa.select(sa.func.count(Comment.id))), 0)
    self.assertIn("This comment is too long", r.get_data(as_text=True))
    ```
    The typed text must still be in the response, so the user keeps it.
  - |
    AC 10 `test_signed_out_sees_login_prompt`: `self.assertIn("Log in to comment", html)`. Also `test_signed_out_post_is_not_saved`: an anonymous `POST` with a body leaves the `Comment` count at 0 and responds with a redirect to `/auth/login`.
  - |
    AC 11 `test_login_prompt_links_to_sign_in`:
    ```python
    self.assertRegex(html, r'<a href="/auth/login[^"]*">\s*Log in to comment')
    ```
  - |
    AC 12 `test_comment_shows_author_timestamp_and_text` asserts the comment's author username and body are in the page, plus a `data-timestamp` attribute inside the comment row (flask-moment renders the time client-side from that attribute, so the server-side HTML carries the ISO timestamp, not "2h ago").
  - |
    AC 13 `test_no_comments_message`:
    ```python
    self.assertIn("No comments yet", self.page(post))
    ```
    Also assert the message is absent once a comment exists.
  - |
    Rollout check `test_migration_head_includes_comment_table`: run the migration chain on SQLite and assert the `comment` table and its indexes exist, or at minimum assert that the new revision's `down_revision` equals the previous head. This is optional if the existing suite has no migration harness; if it has none, note that in the PR instead of adding one.
assumptions_or_open_questions:
  - |
    Deferred question "How are comments protected against spam or rapid repeated posting?" No acceptance criterion asks for it and the scope says nothing about it, so this plan adds NO rate limiting or duplicate detection. Protection is only login-required, CSRF and the 1000-character cap. The reviewer should decide whether a follow-up story is needed. A per-user throttle would be a separate piece of work, since the project has no rate-limiting library today.
  - |
    Deferred question "How many comments per post must the page handle, and does the list need paging?" Not answered by the story. The plan lists ALL comments with no paging. ADR-0007 only sets 25 posts per page and says nothing about comments. If posts are expected to collect hundreds of comments, paging (Newer / Older, as for posts) should be added as a follow-up. The route builds the list with a single ordered query, so paging can be added later without a schema change.
  - |
    The prototype shows like buttons and a collapsed/liked/expanded toggle on the post page. The story does not mention likes (the prototype's own notes say so), and AC 4 says comments are listed when a visitor views the post. The plan builds the comments section always expanded and omits likes. Reviewer: confirm.
  - |
    The prototype's login link only shows a toast because the sign-in page was not named. The app has one, `auth.login` at `/auth/login` (`login_manager.login_view = "auth.login"` in `app/__init__.py`), so the link goes there with `next` set to the post page.
  - |
    Existing routes in `routes.py` are all `@login_required`, so signed-out visitors cannot currently see any post. The new post page is public, as AC 2 and 4 require. The feed pages that link to it stay login-only; a signed-out visitor needs a link or a typed URL to reach a post. Making posts publicly discoverable is out of scope.
  - |
    Comment authors are shown by `username` (the model has no display-name field). The author name is not linked, to keep the comment row as drawn in the prototype.
  - |
    Timestamps use flask-moment `fromNow()`, as in `_post.html`. AC 12 is checked through the `data-timestamp` attribute in server HTML. Exact timestamp wording is not specified by the story.
  - |
    Existing UI strings are translated through Flask-Babel. New strings are wrapped in `_()` and `_l()`, but the Spanish catalog (`app/translations/es/LC_MESSAGES/messages.po`) is not updated in this plan.
  - |
    The existing `base.html` still uses Bootstrap navigation, not the top-bar nav described in the UI guidelines. That nav migration is out of scope here. The post page only uses the design-system content classes inside the existing shell.
estimated_points: 5
package_dependencies: []
notes: |
  ### Data & rollout

  - **Existing data**: the migration only creates a new `comment` table with foreign keys to `post.id` and `user.id`. It does not alter `post`, `user` or any stored row, so all existing rows stay readable. No data migration, so no existing-rows test is needed beyond `test_migration_head_includes_comment_table`.
  - **Backfill / seed**: none. Posts simply start with zero comments and show "No comments yet".
  - **Settings**: no new settings or env vars. The 1000-character limit is a constant in `CommentForm` and in the column length.
  - **Provisioning**: nothing outside the database.
  - **Order and rollback**: deploy by running `flask db upgrade` BEFORE the new code serves traffic, because the post page queries `comment`. Roll back by reverting the code first, then `flask db downgrade` (drops the table and the comments in it). Leaving the empty table in place is also harmless.

  ### Design reference

  Built from `MICROBLOG-STORY-010-design.html`, screen "Post", states `expanded`, `empty`, `too-long` and `signed-out`. Layout is `.post-page stack-lg` capped at `--size-container`. Comments are `ol.comment-list > li.comment` rows with `.divider`-style borders on `--color-border`. The single `.btn-primary` is "Post comment". The signed-out prompt is `.prompt` (a `--color-bg-subtle` fill with a `--radius-lg` border). The `too-long` state has the textarea with `.is-invalid` and a `.field-error`.

  ### Flow

  ```mermaid
  flowchart TD
    Feed[app/templates/_post.html] -->|link to post page| Route[app/main/routes.py post view]
    Route --> Form[app/main/forms.py CommentForm]
    Route --> Model[app/models.py Comment]
    Model --> Mig[migrations/versions comments]
    Route --> Tpl[app/templates/post.html]
    Tpl --> Part[app/templates/_comment.html]
    Tpl --> Css[app/static/comments.css]
    Tpl --> Base[app/templates/base.html]
    Route -.->|signed-out POST| Login[auth.login in app/auth/routes.py]
    classDef touched fill:#f96,color:#000
    class Feed,Route,Form,Model,Mig,Tpl,Part,Css,Base touched
  ```

  `_post.html` is touched to link into the page. The route is public and checks auth itself. `base.html` gets only a `styles` block. `auth.login` is untouched context.

  ### Prompt-injection check

  The work item, deferred questions, current plan and feedback contained no instructions outside the change itself. Nothing was refused.
review_focus: |
  IN scope: the Comment model and migration, CommentForm, the single public `/post/<id>` route, post.html and _comment.html, comments.css on existing tokens, and a link from `_post.html`. OUT: replies, edit/delete, notifications, likes, collapsing, paging and rate limiting (both deferred questions are listed as open assumptions, not solved). Riskiest part: the route is deliberately not `@login_required` while POST must still reject anonymous users and validate CSRF, length and empty text on the server. Also check that the oldest-first order uses the `id` tiebreaker and that comment bodies are autoescaped.
