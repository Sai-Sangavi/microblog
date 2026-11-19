from datetime import datetime, timezone
from flask import (
    render_template,
    flash,
    redirect,
    url_for,
    request,
    g,
    current_app,
    jsonify,
    abort,
    send_from_directory,
)
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError
from flask_login import current_user, login_required
from flask_babel import _, get_locale
import sqlalchemy as sa
from langdetect import detect, LangDetectException
from app import db
from app.main.forms import (
    EditProfileForm,
    EmptyForm,
    PostForm,
    SearchForm,
    MessageForm,
    CommentForm,
    NewPostForm,
)
from sqlalchemy.exc import SQLAlchemyError
from app.models import User, Post, Message, Notification, Comment
from app.translate import translate
from app.main import bp, videos


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


def _detect_language(text):
    try:
        return detect(text)
    except LangDetectException:
        return ""


@bp.route("/new_post", methods=["GET", "POST"])
@login_required
def new_post():
    form = NewPostForm()
    publish_error = False
    token = (form.video_token.data or "").strip()
    if token and not videos.has_pending(current_user.id, token):
        # A token that is not a finished upload can never be published.
        form.video_token.data = token = ""
        if request.method == "POST":
            form.body.errors = []
            form.validate()
            form.body.errors = list(form.body.errors) + [
                _(
                    "Your video isn't ready. Wait until it has finished uploading, then publish."
                )
            ]
            return render_template(
                "new_post.html",
                title=_("New post"),
                form=form,
                publish_error=False,
                video_ready=False,
                video_limit=videos.format_size(current_app.config["VIDEO_MAX_BYTES"]),
            )
    if form.validate_on_submit():
        body = (form.body.data or "").strip()
        try:
            filename = videos.promote(current_user.id, token) if token else None
            post = Post(
                body=body,
                author=current_user,
                language=_detect_language(body) if body else None,
                video_filename=filename,
            )
            db.session.add(post)
            db.session.commit()
        except (SQLAlchemyError, OSError):
            db.session.rollback()
            publish_error = True
        else:
            flash(_("Posted"), "toast")
            return redirect(url_for("main.index"))
    return render_template(
        "new_post.html",
        title=_("New post"),
        form=form,
        publish_error=publish_error,
        video_ready=bool(token),
        video_limit=videos.format_size(current_app.config["VIDEO_MAX_BYTES"]),
    )


def _check_csrf():
    if current_app.config.get("WTF_CSRF_ENABLED", True):
        validate_csrf(
            request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
        )


@bp.route("/new_post/video", methods=["POST"])
@login_required
def upload_video():
    try:
        _check_csrf()
    except ValidationError:
        return jsonify(
            error=_("Your session expired. Reload the page and try again.")
        ), 400
    file = request.files.get("video")
    token = videos.save_pending(current_user.id, file) if file else None
    if token is None:
        return jsonify(error=_("Choose an MP4 or MOV video.")), 400
    return jsonify(token=token)


@bp.route("/new_post/video/<token>", methods=["DELETE"])
@login_required
def discard_video(token):
    try:
        _check_csrf()
    except ValidationError:
        return jsonify(
            error=_("Your session expired. Reload the page and try again.")
        ), 400
    videos.delete_pending(current_user.id, token)
    return "", 204


@bp.app_errorhandler(413)
def video_too_large(error):
    if request.path == url_for("main.upload_video"):
        return jsonify(error=_("That video is too large.")), 413
    return error


@bp.route("/media/video/<filename>")
@login_required
def post_video(filename):
    if not videos.FINAL_NAME_RE.match(filename):
        abort(404)
    return send_from_directory(videos.final_dir(), filename, conditional=True)


@bp.route("/", methods=["GET", "POST"])
@bp.route("/index", methods=["GET", "POST"])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        language = _detect_language(form.post.data)
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_("Your post is now live!"))
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    posts = db.paginate(
        current_user.following_posts(),
        page=page,
        per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=False,
    )
    next_url = url_for("main.index", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("main.index", page=posts.prev_num) if posts.has_prev else None
    return render_template(
        "index.html",
        title=_("Home"),
        form=form,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
    )


@bp.route("/explore")
@login_required
def explore():
    page = request.args.get("page", 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(
        query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = url_for("main.explore", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("main.explore", page=posts.prev_num) if posts.has_prev else None
    return render_template(
        "index.html",
        title=_("Explore"),
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
    )


# Public on purpose (no @login_required): signed-out visitors can read the
# comments. The POST branch checks authentication itself.
@bp.route("/post/<int:id>", methods=["GET", "POST"])
def post(id):
    post = db.get_or_404(Post, id)
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        db.session.add(Comment(body=form.body.data, post=post, author=current_user))
        db.session.commit()
        flash(_("Your comment is posted"))
        return redirect(url_for("main.post", id=post.id) + "#comments")
    comments = db.session.scalars(
        post.comments.select().order_by(Comment.timestamp.asc(), Comment.id.asc())
    ).all()
    return render_template(
        "post.html", title=_("Post"), post=post, form=form, comments=comments
    )


@bp.route("/user/<username>")
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get("page", 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(
        query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = (
        url_for("main.user", username=user.username, page=posts.next_num)
        if posts.has_next
        else None
    )
    prev_url = (
        url_for("main.user", username=user.username, page=posts.prev_num)
        if posts.has_prev
        else None
    )
    form = EmptyForm()
    return render_template(
        "user.html",
        user=user,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
        form=form,
    )


@bp.route("/user/<username>/popup")
@login_required
def user_popup(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    form = EmptyForm()
    return render_template("user_popup.html", user=user, form=form)


@bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_("Your changes have been saved."))
        return redirect(url_for("main.edit_profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", title=_("Edit Profile"), form=form)


@bp.route("/follow/<username>", methods=["POST"])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(_("User %(username)s not found.", username=username))
            return redirect(url_for("main.index"))
        if user == current_user:
            flash(_("You cannot follow yourself!"))
            return redirect(url_for("main.user", username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_("You are following %(username)s!", username=username))
        return redirect(url_for("main.user", username=username))
    else:
        return redirect(url_for("main.index"))


@bp.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(_("User %(username)s not found.", username=username))
            return redirect(url_for("main.index"))
        if user == current_user:
            flash(_("You cannot unfollow yourself!"))
            return redirect(url_for("main.user", username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_("You are not following %(username)s.", username=username))
        return redirect(url_for("main.user", username=username))
    else:
        return redirect(url_for("main.index"))


@bp.route("/translate", methods=["POST"])
@login_required
def translate_text():
    data = request.get_json()
    return {
        "text": translate(data["text"], data["source_language"], data["dest_language"])
    }


@bp.route("/search")
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for("main.explore"))
    page = request.args.get("page", 1, type=int)
    posts, total = Post.search(
        g.search_form.q.data, page, current_app.config["POSTS_PER_PAGE"]
    )
    next_url = (
        url_for("main.search", q=g.search_form.q.data, page=page + 1)
        if total > page * current_app.config["POSTS_PER_PAGE"]
        else None
    )
    prev_url = (
        url_for("main.search", q=g.search_form.q.data, page=page - 1)
        if page > 1
        else None
    )
    return render_template(
        "search.html",
        title=_("Search"),
        posts=posts,
        next_url=next_url,
        prev_url=prev_url,
    )


@bp.route("/send_message/<recipient>", methods=["GET", "POST"])
@login_required
def send_message(recipient):
    user = db.first_or_404(sa.select(User).where(User.username == recipient))
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user, body=form.message.data)
        db.session.add(msg)
        user.add_notification("unread_message_count", user.unread_message_count())
        db.session.commit()
        flash(_("Your message has been sent."))
        return redirect(url_for("main.user", username=recipient))
    return render_template(
        "send_message.html", title=_("Send Message"), form=form, recipient=recipient
    )


@bp.route("/messages")
@login_required
def messages():
    current_user.last_message_read_time = datetime.now(timezone.utc)
    current_user.add_notification("unread_message_count", 0)
    db.session.commit()
    page = request.args.get("page", 1, type=int)
    query = current_user.messages_received.select().order_by(Message.timestamp.desc())
    messages = db.paginate(
        query, page=page, per_page=current_app.config["POSTS_PER_PAGE"], error_out=False
    )
    next_url = (
        url_for("main.messages", page=messages.next_num) if messages.has_next else None
    )
    prev_url = (
        url_for("main.messages", page=messages.prev_num) if messages.has_prev else None
    )
    return render_template(
        "messages.html", messages=messages.items, next_url=next_url, prev_url=prev_url
    )


@bp.route("/export_posts")
@login_required
def export_posts():
    if current_user.get_task_in_progress("export_posts"):
        flash(_("An export task is currently in progress"))
    else:
        current_user.launch_task("export_posts", _("Exporting posts..."))
        db.session.commit()
    return redirect(url_for("main.user", username=current_user.username))


@bp.route("/notifications")
@login_required
def notifications():
    since = request.args.get("since", 0.0, type=float)
    query = (
        current_user.notifications.select()
        .where(Notification.timestamp > since)
        .order_by(Notification.timestamp.asc())
    )
    notifications = db.session.scalars(query)
    return [
        {"name": n.name, "data": n.get_data(), "timestamp": n.timestamp}
        for n in notifications
    ]
