# coding: utf-8
from flask import request, render_template, session, redirect, url_for, abort

from . import app, db
from .forms import AuthForm, KeyForm, utctime_to_localstring
from .models import AccessKey
from mailtank import MailtankError


@app.route('/', methods=['GET', 'POST'])
def index():
    """Вьюшка с формой ввода ключа от Mailtank"""
    form = AuthForm(request.form)

    if form.validate_on_submit():
        key = AccessKey.query.filter_by(content=form.mailtank_key.data).first() \
            or AccessKey(content=form.mailtank_key.data, namespace='')

        try:
            key.mailtank.get_tags()
        except MailtankError as e:
            form.mailtank_key.errors.append(
                u'Невозможно войти по такому ключу Mailtank из-за ошибки'
                u'"{}"'.format(e))
        else:
            session['key'] = key.content
            db.session.add(key)
            db.session.commit()
            return redirect(url_for('key'))

    session.pop('key', None)
    return render_template('index.html', form=form)


@app.route('/key/', methods=['GET', 'POST'])
def key():
    """Вьюшка, позволяющая менять настройки ключа от Mailtank в системе.
    Ожидает, что в session лежит ключ 'key', уже созданный в базе данных.
    """
    key_content = session.get('key') or abort(403)
    key = AccessKey.query.filter_by(content=key_content).first_or_404()
    form_kwargs = {}
    if request.method == 'GET':
        form_kwargs = {
            'local_first_send_interval_start': utctime_to_localstring(
                key.first_send_interval_start, key.timezone),
            'local_first_send_interval_end': utctime_to_localstring(
                key.first_send_interval_end, key.timezone)}

    form = KeyForm(request.form, obj=key, **form_kwargs)

    if form.validate_on_submit():
        form.populate_obj(key)
        db.session.add(key)
        db.session.commit()

    return render_template('key.html', key=key, form=form)
