from flask import request
from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Length, Optional
import sqlalchemy as sa
from flask_babel import _, lazy_gettext as _l
from app import db
from app.models import User


class EditProfileForm(FlaskForm):
    username = StringField(_l("Username"), validators=[DataRequired()])
    about_me = TextAreaField(_l("About me"), validators=[Length(min=0, max=140)])
    submit = SubmitField(_l("Submit"))

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(
                sa.select(User).where(User.username == username.data)
            )
            if user is not None:
                raise ValidationError(_("Please use a different username."))


class EmptyForm(FlaskForm):
    submit = SubmitField("Submit")


class PostForm(FlaskForm):
    post = TextAreaField(
        _l("Say something"), validators=[DataRequired(), Length(min=1, max=140)]
    )
    submit = SubmitField(_l("Submit"))


class NewPostForm(FlaskForm):
    body = TextAreaField(
        _l("Post text"),
        validators=[
            Optional(),
            Length(
                max=140, message=_l("Shorten your post to 140 characters to publish.")
            ),
        ],
    )
    video_token = HiddenField()
    submit = SubmitField(_l("Publish"))

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        if ok and not (self.body.data or "").strip() and not self.video_token.data:
            self.body.errors = list(self.body.errors) + [
                _("Write something before you publish.")
            ]
            return False
        return ok


class SearchForm(FlaskForm):
    q = StringField(_l("Search"), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if "formdata" not in kwargs:
            kwargs["formdata"] = request.args
        if "meta" not in kwargs:
            kwargs["meta"] = {"csrf": False}
        super(SearchForm, self).__init__(*args, **kwargs)


class CommentForm(FlaskForm):
    body = TextAreaField(
        _l("Add a comment"),
        validators=[
            DataRequired(message=_l("Write something before you post.")),
            Length(
                min=1,
                max=1000,
                message=_l(
                    "This comment is too long. Shorten it to 1000 characters to post."
                ),
            ),
        ],
    )
    submit = SubmitField(_l("Post comment"))


class MessageForm(FlaskForm):
    message = TextAreaField(
        _l("Message"), validators=[DataRequired(), Length(min=1, max=140)]
    )
    submit = SubmitField(_l("Submit"))
