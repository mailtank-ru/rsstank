# coding: utf-8
import datetime as dt

import pytz
from flask.ext import wtf
import wtforms


class TimeString(wtforms.validators.Regexp):
    """Валидирует поле, содержащее время вида ЧЧ:мм:сс"""
    def __init__(self, message=None):
        super(TimeString, self).__init__(r'^([0-1]\d|2[0-3]):[0-5]\d:[0-5]\d$')

    def __call__(self, form, field):
        message = self.message
        if message is None:
            message = field.gettext(u'Неправильный формат времени.')

        super(TimeString, self).__call__(form, field, message)


class AuthForm(wtf.Form):
    """Форма аутентификации по ключу"""
    mailtank_key = wtforms.TextField(u'Ключ проекта Mailtank', [wtforms.validators.Required()])


def utctime_from_localstring(time_str, tz):
    """Преобразует строковое представление времени `time_str` с часовым поясом
    `tz` в :class:`datetime.time` с часовым поясом UTC
    """
    t = dt.datetime.strptime(time_str, '%H:%M:%S').time()
    dtime = dt.datetime.combine(dt.date.today(), t)
    local_dtime = pytz.timezone(tz).localize(dtime)
    utc_dt = local_dtime.astimezone(pytz.UTC)
    return utc_dt.time()


def utctime_to_localstring(t, tz):
    """Преобразует `t` класса :class:`datetime.time` в строку, используя часовой
    пояс из строки `tz`
    """
    dtime = dt.datetime.combine(dt.date.today(), t).replace(tzinfo=pytz.UTC)
    local_dt = dtime.astimezone(pytz.timezone(tz))
    return local_dt.strftime('%H:%M:%S')


class KeyForm(wtf.Form):
    """Форма редактирования настроек для ключа"""
    is_enabled = wtforms.BooleanField(u'Включен', [wtforms.validators.NumberRange(0, 1)])
    namespace = wtforms.TextField(u'Пространство имен (маска для тэгов)')
    timezone = wtforms.TextField(u'Часовой пояс', [wtforms.validators.Required()])
    local_first_send_interval_start = \
        wtforms.TextField(u'Начало временного промежутка первой рассылки',
                          [wtforms.validators.Required(), TimeString()])
    local_first_send_interval_end = \
        wtforms.TextField(u'Конец временного промежутка первой рассылки',
                          [wtforms.validators.Required(), TimeString()])

    def __init__(self, *args, **kwargs):
        super(KeyForm, self).__init__(*args, **kwargs)
        key = kwargs.get('obj', None)
        if key:
            if not self.local_first_send_interval_start.data:
                self.local_first_send_interval_start.data = \
                    utctime_to_localstring(key.first_send_interval_start, key.timezone)
            if not self.local_first_send_interval_end.data:
                self.local_first_send_interval_end.data = \
                    utctime_to_localstring(key.first_send_interval_end, key.timezone)

    def validate_timezone(form, field):
        try:
            pytz.timezone(field.data)
        except pytz.UnknownTimeZoneError:
            field.errors.append(u'Неправильный часовой пояс')
            return False

        return True

    def populate_obj(self, key):
        super(KeyForm, self).populate_obj(key)
        key.first_send_interval_start = utctime_from_localstring(
            self.local_first_send_interval_start.data,
            self.timezone.data)
        key.first_send_interval_end = utctime_from_localstring(
            self.local_first_send_interval_end.data,
            self.timezone.data)
