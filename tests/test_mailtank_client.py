import json
import pytest

import furl
import httpretty

import mailtank
from . import TestCase


PAGES_DATA = [{
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
    'pages_total': 3,
}, {
    'objects': [
        {'name': 'tag_17499'},
        {'name': 'tag_15097'},
        {'name': 'tag_22078'},
        {'name': 'tag_22622'},
        {'name': 'tag_10538'},
        {'name': 'tag_2743'},
        {'name': 'tag_18477'},
        {'name': 'tag_10932'},
        {'name': 'tag_20410'},
        {'name': 'tag_7900'},
    ],
    'page': 2,
    'pages_total': 3,
}, {
    'objects': [
        {'name': 'tag_9545'},
        {'name': 'tag_22437'},
        {'name': 'tag_4283'},
        {'name': 'tag_21889'},
        {'name': 'tag_2889'},
        {'name': 'tag_19389'},
        {'name': 'tag_23564'},
    ],
    'page': 3,
    'pages_total': 3,
}]

MAILING_DATA = {
    'eta': None,
    'id': 16,
    'status': 'ENQUEUED',
    'url': '/mailings/16'
}


class TestMailtankClient(TestCase):
    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.m = mailtank.Mailtank('http://api.mailtank.ru', 'pumpurum')

    @httpretty.httprettified
    def test_get_tags(self):
        def request_callback(method, uri, headers):
            page = int(furl.furl(uri).args['page'])
            return (200, headers, json.dumps(PAGES_DATA[page - 1]))

        httpretty.register_uri(
            httpretty.GET, 'http://api.mailtank.ru/tags/',
            body=request_callback)

        tags = self.m.get_tags()

        assert len(tags) == sum(len(page['objects']) for page in PAGES_DATA)
        assert tags[0].name == 'type_main_news'
        assert tags[5].name == 'tag_11592'
        assert tags[-1].name == 'tag_23564'

    @httpretty.httprettified
    def test_create_mailing(self):
        httpretty.register_uri(
            httpretty.POST, 'http://api.mailtank.ru/mailings/',
            responses=[httpretty.Response(body=json.dumps(MAILING_DATA),
                                          status=200,
                                          content_type='text/json'),
                       httpretty.Response(body='',
                                          status=500)])

        mailing = self.m.create_mailing('e25388fde8',
                                        {'name': 'Max'},
                                        {'tags': ['asdf'],
                                         'unsubscribe_tags': ['asdf']})

        assert mailing.id == 16
        assert mailing.url == '/mailings/16'
        assert mailing.status == 'ENQUEUED'
        assert mailing.eta is None

        with pytest.raises(mailtank.MailtankError) as excinfo:
            mailing = self.m.create_mailing('e25388fde8', {}, {})

        assert str(excinfo.value) == '500 <Response [500]>'
