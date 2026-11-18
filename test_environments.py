import unittest
import sqlalchemy as sa
from app import create_app, db
from app.models import User, Project, Environment, Variable, VariableOverride
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


def make_project(user, name="Demo"):
    p = Project(name=name, user_id=user.id)
    db.session.add(p)
    db.session.commit()
    return p


def make_env(project, name):
    e = Environment(project_id=project.id, name=name)
    db.session.add(e)
    db.session.commit()
    return e


def make_var(project, key, value, sensitive=False):
    v = Variable(
        project_id=project.id, key=key, shared_value=value, is_sensitive=sensitive
    )
    db.session.add(v)
    db.session.commit()
    return v


def make_override(var, env, value):
    o = VariableOverride(variable_id=var.id, environment_id=env.id, value=value)
    db.session.add(o)
    db.session.commit()
    return o


class Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.user = make_user()
        self.project = make_project(self.user)
        self.staging = make_env(self.project, "staging")
        self.production = make_env(self.project, "production")
        self.client = self.app.test_client()
        self.client.post("/auth/login", data={"username": "susan", "password": "cat"})
        self.url = f"/projects/{self.project.id}/environments"

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def page(self, env):
        return self.client.get(f"{self.url}?env={env.id}").get_data(as_text=True)


class EnvironmentsSectionTests(Base):
    def test_section_is_shown(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Environments and variables", r.get_data(as_text=True))

    def test_other_users_project_is_404(self):
        other = make_user("mary")
        p = make_project(other, "Other")
        r = self.client.get(f"/projects/{p.id}/environments")
        self.assertEqual(r.status_code, 404)


class EnvironmentTests(Base):
    def test_create_environment_is_listed(self):
        r = self.client.post(self.url, data={"name": "qa"}, follow_redirects=True)
        self.assertIn("qa", r.get_data(as_text=True))
        self.assertEqual(
            db.session.scalar(
                sa.select(Environment).where(Environment.name == "qa")
            ).project_id,
            self.project.id,
        )

    def test_duplicate_name_rejected(self):
        self.client.post(self.url, data={"name": "staging"}, follow_redirects=True)
        count = db.session.scalar(
            sa.select(sa.func.count())
            .select_from(Environment)
            .where(Environment.name == "staging")
        )
        self.assertEqual(count, 1)

    def test_delete_environment_not_listed(self):
        env = make_env(self.project, "qa-env")
        r = self.client.post(f"{self.url}/{env.id}/delete", follow_redirects=True)
        self.assertNotIn("qa-env", r.get_data(as_text=True))
        self.assertIsNone(db.session.get(Environment, env.id))

    def test_delete_environment_removes_overrides(self):
        var = make_var(self.project, "LOG_LEVEL", "info")
        make_override(var, self.staging, "debug")
        self.client.post(f"{self.url}/{self.staging.id}/delete")
        db.session.expire_all()
        self.assertEqual(
            db.session.scalar(sa.select(sa.func.count()).select_from(VariableOverride)),
            0,
        )

    def test_set_override_via_form(self):
        var = make_var(self.project, "LOG_LEVEL", "info")
        self.client.post(
            f"/projects/{self.project.id}/variables/{var.id}/overrides",
            data={"environment_id": self.staging.id, "value": "debug"},
        )
        self.assertIn("debug", self.page(self.staging))
        self.assertNotIn("debug", self.page(self.production))


class VariableValueTests(Base):
    def test_shared_value_shown(self):
        var = make_var(self.project, "LOG_LEVEL", "info")
        self.assertIn("info", self.page(self.staging))
        self.assertEqual(var.value_for(self.staging), "info")

    def test_override_shown_in_its_environment(self):
        var = make_var(self.project, "LOG_LEVEL", "info")
        make_override(var, self.staging, "debug")
        self.assertIn("debug", self.page(self.staging))

    def test_other_environment_shows_shared(self):
        var = make_var(self.project, "LOG_LEVEL", "info")
        make_override(var, self.staging, "debug")
        body = self.page(self.production)
        self.assertIn("info", body)
        self.assertNotIn("debug", body)


class SensitiveVariableTests(Base):
    def test_value_is_masked(self):
        self.client.post(
            f"/projects/{self.project.id}/variables",
            data={
                "key": "API_KEY",
                "shared_value": "hunter2-secret",
                "is_sensitive": "y",
            },
        )
        body = self.page(self.staging)
        self.assertIn("API_KEY", body)
        self.assertNotIn("hunter2-secret", body)
        self.assertIn(Variable.MASK, body)

    def test_overridden_value_is_masked(self):
        var = make_var(self.project, "API_KEY", "hunter2-secret", True)
        make_override(var, self.staging, "override-secret")
        body = self.page(self.staging)
        self.assertNotIn("hunter2-secret", body)
        self.assertNotIn("override-secret", body)
        self.assertIn(Variable.MASK, body)

    def test_no_reveal_control(self):
        var = make_var(self.project, "API_KEY", "hunter2-secret", True)
        body = self.page(self.staging).lower()
        for word in ("reveal", "show value", "unmask", 'type="password"'):
            self.assertNotIn(word, body)
        self.assertNotIn("hunter2-secret", body)
        r = self.client.get(f"/projects/{self.project.id}/variables/{var.id}")
        self.assertEqual(r.status_code, 404)


class MigrationTests(Base):
    def test_user_loads_and_project_delete_cascades(self):
        self.assertIsNotNone(db.session.get(User, self.user.id))
        var = make_var(self.project, "K", "v")
        make_override(var, self.staging, "x")
        db.session.delete(self.project)
        db.session.commit()
        for model in (Environment, Variable, VariableOverride):
            self.assertEqual(
                db.session.scalar(sa.select(sa.func.count()).select_from(model)), 0
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
