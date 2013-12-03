# coding: utf-8
import datetime as dt

import pytz
from flask.ext import wtf
import wtforms


class AuthForm(wtf.Form):
    """Форма аутентификации по ключу"""
    mailtank_key = wtforms.TextField(u'Ключ проекта Mailtank', [wtforms.validators.Required()])


def utctime_from_localstring(hour, tz):
    """Преобразует `hour` с часовым поясом
    `tz` в :class:`datetime.time` с часовым поясом UTC
    """
    t = dt.time(hour=int(hour))
    dtime = dt.datetime.combine(dt.date.today(), t)
    local_dtime = pytz.timezone(tz).localize(dtime)
    utc_dt = local_dtime.astimezone(pytz.UTC)
    return utc_dt.time()


def utctime_to_localstring(t, tz):
    """Преобразует `t` класса :class:`datetime.time` в часы, используя часовой
    пояс из строки `tz`
    """
    dtime = dt.datetime.combine(dt.date.today(), t).replace(tzinfo=pytz.UTC)
    local_dt = dtime.astimezone(pytz.timezone(tz))
    return local_dt.hour


class KeyForm(wtf.Form):
    """Форма редактирования настроек для ключа"""
    is_enabled = wtforms.BooleanField(u'Включен',
                                      [wtforms.validators.NumberRange(0, 1)])
    namespace = wtforms.TextField(u'Пространство имен (маска для тегов)',
                                  [wtforms.validators.Required()])
    timezone = wtforms.SelectField(u'Часовой пояс',
                                   choices=[(tz, tz) for tz in pytz.common_timezones])
    local_first_send_interval_start = \
        wtforms.SelectField(u'Начало временного промежутка первой рассылки',
                            choices=[(i, '{}:00'.format(i)) for i in range(0, 24)],
                            coerce=int)
    local_first_send_interval_end = \
        wtforms.SelectField(u'Конец временного промежутка первой рассылки',
                            choices=[(i, '{}:00'.format(i)) for i in range(0, 24)],
                            coerce=int)

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
