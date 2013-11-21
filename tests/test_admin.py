from flask import url_for

from . import TestCase


class TestAdmin(TestCase):
    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.index_url = url_for('index')

    def test_auth(self):
        r = self.client.get(self.index_url)
        r.form['mailtank_key'] = 'asdf'
        r = r.form.submit()
