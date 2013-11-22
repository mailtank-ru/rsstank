# coding: utf-8
import json

from flask import url_for
import httpretty

from . import TestCase
from rsstank import db
from rsstank.models import AccessKey

TAGS_DATA = {
    'objects': [
        {u'name': 'type_main_news'},
        {'name': 'type_spec'},
        {'name': ''},
        {'name': 'type_unknown'},
        {'name': 'tag_7523'},
        {'name': 'tag_11592'},
        {'name': 'tag_23517'},
        {'name': 'tag_7447'},
        {'name': 'tag_23758'},
        {'name': 'tag_23464'},
    ],
    'page': 1,
    'pages_total': 1,
}


class TestAdmin(TestCase):
    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.index_url = url_for('index')

    @httpretty.httprettified
    def test_auth(self):
        """Клиент может зайти по ключу Mailtank. Если ключа не было, он создается"""
        httpretty.register_uri(
            httpretty.GET, '{}/tags'.format(self.app.config['MAILTANK_API_URL']),
            responses=[
                httpretty.Response(body='', status=403),
                httpretty.Response(body=json.dumps(TAGS_DATA),
                                   status=200,
                                   content_type='text/json')])

        # Первая попытка неудачна
        r = self.client.get(self.index_url)
        r.form['mailtank_key'] = 'asdfg'
        r = r.form.submit()
        assert len(r.context['form'].mailtank_key.errors) == 1

        # Вторая попытка удачна
        r = self.client.get(self.index_url)
        r.form['mailtank_key'] = 'asdf'
        r = r.form.submit().follow()
        
        # Проверяем, что ключ создался
        a = AccessKey.query.first()
        assert (a.content, a.is_enabled, a.namespace) == ('asdf', False, '')
        
    @httpretty.httprettified
    def test_edit(self):
        """Клиент может изменять свойства ключа"""
        httpretty.register_uri(
            httpretty.GET, '{}/tags'.format(self.app.config['MAILTANK_API_URL']),
            body=json.dumps(TAGS_DATA), status=200, content_type='text/json')

        a = AccessKey(content='asdf', namespace='')
        db.session.add(a)
        db.session.commit()

        # Входим в систему по ключу
        r = self.client.get(self.index_url)
        r.form['mailtank_key'] = 'asdf'
        r = r.form.submit().follow()

        # Изменяем маску (пространство имен)
        form = r.form
        form['namespace'] = 'mask'
        r = form.submit()

        a = AccessKey.query.first()
        assert (a.content, a.is_enabled, a.namespace) == ('asdf', False, 'mask')

        # Изменяем состояние на "Включен"
        form['is_enabled'] = 1
        r = form.submit()

        a = AccessKey.query.first()
        assert (a.content, a.is_enabled, a.namespace) == ('asdf', True, 'mask')
