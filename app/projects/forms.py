from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Length
import sqlalchemy as sa
from flask_babel import _, lazy_gettext as _l
from app import db
from app.models import Environment, Variable


class EnvironmentForm(FlaskForm):
    name = StringField(
        _l("Environment name"), validators=[DataRequired(), Length(max=64)]
    )
    submit = SubmitField(_l("Create environment"))

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project

    def validate_name(self, name):
        exists = db.session.scalar(
            sa.select(Environment).where(
                Environment.project_id == self.project.id, Environment.name == name.data
            )
        )
        if exists is not None:
            raise ValidationError(_("An environment with this name exists."))


class VariableForm(FlaskForm):
    key = StringField(_l("Key"), validators=[DataRequired(), Length(max=128)])
    shared_value = StringField(_l("Shared value"))
    is_sensitive = BooleanField(_l("Sensitive"))
    submit = SubmitField(_l("Add variable"))

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project

    def validate_key(self, key):
        exists = db.session.scalar(
            sa.select(Variable).where(
                Variable.project_id == self.project.id, Variable.key == key.data
            )
        )
        if exists is not None:
            raise ValidationError(_("A variable with this key exists."))


class OverrideForm(FlaskForm):
    environment_id = SelectField(_l("Environment"), coerce=int)
    value = StringField(_l("Override value"))
    submit = SubmitField(_l("Set override"))
