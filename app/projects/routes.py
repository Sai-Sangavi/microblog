from flask import Blueprint, render_template, redirect, url_for, request, abort, flash
from flask_babel import _
from flask_login import current_user, login_required
from app import db
from app.main.forms import EmptyForm
from app.models import Project, Environment, Variable, VariableOverride
from app.projects.forms import EnvironmentForm, VariableForm, OverrideForm

bp = Blueprint("projects", __name__)


def get_owned_project(project_id):
    project = db.get_or_404(Project, project_id)
    if project.user_id != current_user.id:
        abort(404)
    return project


def section_url(project, environment=None):
    if environment is None:
        return url_for("projects.environments", project_id=project.id)
    return url_for("projects.environments", project_id=project.id, env=environment.id)


def render_section(project, environment_form=None, variable_form=None):
    environments = db.session.scalars(
        project.environments.select().order_by(Environment.name)
    ).all()
    selected = None
    env_id = request.args.get("env", type=int)
    if env_id is not None:
        selected = next((e for e in environments if e.id == env_id), None)
    if selected is None and environments:
        selected = environments[0]
    variables = db.session.scalars(
        project.variables.select().order_by(Variable.key)
    ).all()
    override_form = OverrideForm()
    override_form.environment_id.choices = [(e.id, e.name) for e in environments]
    if selected is not None:
        override_form.environment_id.data = selected.id
    return render_template(
        "projects/environments.html",
        title=_("Environments and variables"),
        project=project,
        environments=environments,
        selected=selected,
        variables=variables,
        environment_form=environment_form or EnvironmentForm(project),
        variable_form=variable_form or VariableForm(project),
        override_form=override_form,
        delete_form=EmptyForm(),
    )


@bp.route("/projects/<int:project_id>/environments")
@login_required
def environments(project_id):
    return render_section(get_owned_project(project_id))


@bp.route("/projects/<int:project_id>/environments", methods=["POST"])
@login_required
def create_environment(project_id):
    project = get_owned_project(project_id)
    form = EnvironmentForm(project)
    if form.validate_on_submit():
        env = Environment(project_id=project.id, name=form.name.data)
        db.session.add(env)
        db.session.commit()
        flash(_("Environment created."))
        return redirect(section_url(project, env))
    return render_section(project, environment_form=form)


@bp.route(
    "/projects/<int:project_id>/environments/<int:environment_id>/delete",
    methods=["POST"],
)
@login_required
def delete_environment(project_id, environment_id):
    project = get_owned_project(project_id)
    form = EmptyForm()
    if form.validate_on_submit():
        env = db.session.get(Environment, environment_id)
        if env is None or env.project_id != project.id:
            abort(404)
        db.session.delete(env)
        db.session.commit()
        flash(_("Environment deleted."))
    return redirect(section_url(project))


@bp.route("/projects/<int:project_id>/variables", methods=["POST"])
@login_required
def create_variable(project_id):
    project = get_owned_project(project_id)
    form = VariableForm(project)
    if form.validate_on_submit():
        db.session.add(
            Variable(
                project_id=project.id,
                key=form.key.data,
                shared_value=form.shared_value.data or "",
                is_sensitive=form.is_sensitive.data,
            )
        )
        db.session.commit()
        flash(_("Variable added."))
        return redirect(section_url(project))
    return render_section(project, variable_form=form)


@bp.route(
    "/projects/<int:project_id>/variables/<int:variable_id>/overrides", methods=["POST"]
)
@login_required
def set_override(project_id, variable_id):
    project = get_owned_project(project_id)
    variable = db.session.get(Variable, variable_id)
    if variable is None or variable.project_id != project.id:
        abort(404)
    form = OverrideForm()
    form.environment_id.choices = [
        (e.id, e.name) for e in db.session.scalars(project.environments.select())
    ]
    if not form.validate_on_submit():
        abort(400)
    env = db.session.get(Environment, form.environment_id.data)
    if env is None or env.project_id != project.id:
        abort(404)
    override = db.session.scalar(
        variable.overrides.select().where(VariableOverride.environment_id == env.id)
    )
    if override is None:
        db.session.add(
            VariableOverride(
                variable_id=variable.id,
                environment_id=env.id,
                value=form.value.data or "",
            )
        )
    else:
        override.value = form.value.data or ""
    db.session.commit()
    flash(_("Override saved."))
    return redirect(section_url(project, env))
