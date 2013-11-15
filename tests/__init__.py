import rsstank


class SQLAlchemyMixin(object):
    @property
    def db(self):
        return self.app.extensions['sqlalchemy'].db
    
    def create_database(self):
        self.db.create_all()
    
    def drop_database(self):
        self.db.drop_all()


class SQLAlchemyFixtureMixin(object):
    def get_fixtures(self):
        return getattr(self, 'FIXTURES', [])

    def load_fixtures(self):
        for fixture in self.get_fixtures():
            if callable(fixture):
                models_to_merge = fixture()
                if isinstance(models_to_merge, db.Model):
                    models_to_merge = [models_to_merge]
            elif isinstance(fixture, (list, set)):
                models_to_merge = fixture
            elif isinstance(fixture, self.db.Model):
                models_to_merge = [fixture]
            else:
                raise AssertionError(
                    'Don\'t know how to handle fixture of {} '
                    'type: {}.'.format(type(fixture), fixture))
            for model in models_to_merge:
                self.db.session.merge(model)
                self.db.session.commit()
        self.db.session.remove()


class TestCase(SQLAlchemyMixin, SQLAlchemyFixtureMixin):
    def setup_method(self, method):
        self.app = rsstank.app
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.drop_database()
        self.create_database()
        self.load_fixtures()
    
    def teardown_method(self, method):
        self.db.session.remove()
        self.ctx.pop()
