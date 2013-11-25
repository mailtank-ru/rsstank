# coding: utf-8
import json
import logging
from urlparse import urljoin

from requests import session


class MailtankError(Exception):
    def __init__(self, response):
        super(MailtankError, self).__init__(response)
        #: Ответ API, который послужил причиной ошибки
        self.response = response
        #: Статус ответа API, послужившего причиной ошибки
        self.code = self.response.status_code
        try:
            errors = self.response.json()
            if self.code == 400:
                self.message = unicode(errors)
            else:
                self.message = errors.get('message')
        except:
            self.message = self.response

    def __repr__(self):
        return '<MailtankError [{0}]>'.format(self.message or self.code)

    def __str__(self):
        return '{0} {1}'.format(self.code, self.message)


class Mailtank(object):
    def __init__(self, api_url, api_key):
        self._api_url = api_url
        self._api_key = api_key
        self._session = session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'rsstank',
            'X-Auth-Token': self._api_key,
        })
        self._logger = logging.getLogger(__name__)

    def _delete(self, url, **kwargs):
        self._logger.debug('DELETE %s with %s', url, kwargs)
        return self._session.delete(url, **kwargs)

    def _json(self, response):
        if not 200 <= response.status_code < 400:
            raise MailtankError(response)
        try:
            return response.json()
        except ValueError:
            raise MailtankError(response)

    def _get(self, url, **kwargs):
        self._logger.debug('GET %s with %s', url, kwargs)
        return self._session.get(url, **kwargs)

    def _patch(self, url, **kwargs):
        self._logger.debug('PATCH %s with %s', url, kwargs)
        return self._session.patch(url, **kwargs)

    def _post(self, url, data, **kwargs):
        self._logger.debug('POST %s with %s, %s', url, data, kwargs)
        return self._session.post(url, data, **kwargs)

    def _put(self, url, **kwargs):
        self._logger.debug('PUT %s with %s', url, kwargs)
        return self._session.put(url, **kwargs)

    def get_tags(self, mask=None):
        # TODO Не загружать все страницы сразу, возвращать итератор по тегам,
        # который будет подгружать страницы по мере необходимости

        def fetch_page(n):
            return self._json(self._get(
                urljoin(self._api_url, 'tags'),
                params={
                    'mask': mask,
                    # API Mailtank считает страницы с единицы
                    'page': current_page + 1,
                }))

        # Первая страница есть всегда; необходимо запросить её вне цикла
        # затем, чтобы узнать общее количество страниц
        current_page = 0
        first_page = fetch_page(current_page)
        pages_total = first_page['pages_total']
        rv = map(Tag, first_page['objects'])

        # Начинаем цикл со второй страницы, так как первую уже обработали
        current_page = 1
        while current_page < pages_total:
            page = fetch_page(current_page)
            rv += map(Tag, page['objects'])
            current_page += 1

        return rv

    def create_mailing(self, layout_id, context, target, attachments=None):
        """Создает и выполняет рассылку Mailtank. Возвращает :class:`Mailing`
        :param layout_id: идентификатор шаблона, который будет
                                     использован для рассылки
        :type layout_id: str

        :param context: словарь, содержащий данные рассылки. Должен
                                 удовлетворять структуре используемого шаблона
        :type context: dict

        :param target: словарь, задающий получателей рассылки.
        :type target: dict

        :param attachments: (опционально) список словарей, описывающих вложения
        :type attachments: list
        """
        data = {
            'context': context,
            'layout_id': layout_id,
            'target': target,
        }
        if attachments:
            data['attachments'] = attachments

        response = self._json(self._post(
            urljoin(self._api_url, 'mailings/'),
            data=json.dumps(data)))

        return Mailing(response)


class Tag(object):
    def __init__(self, data):
        self.name = data.get('name')


class Mailing(object):
    def __init__(self, data):
        self.eta = data.get('eta')
        self.id = data.get('id')
        self.status = data.get('status')
        self.url = data.get('url')
