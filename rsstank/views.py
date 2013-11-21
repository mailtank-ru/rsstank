# coding: utf-8
from flask import request, render_template, session, redirect, url_for

from . import app, db
from forms import AuthForm, KeyForm
from models import AccessKey
from mailtank import MailtankError


@app.route('/', methods=['GET', 'POST'])
def index():
    """Вьюшка с формой ввода ключа от Mailtank"""
    form = AuthForm(request.form)

    if form.validate_on_submit():
        key = AccessKey.query.filter_by(content=form.mailtank_key.data).first() \
            or AccessKey(content=form.mailtank_key.data, namespace='')

        mailtank = key.mailtank()
        try:
            mailtank.get_tags()
        except MailtankError as e:
            form.mailtank_key.errors.append(u'Невозможно войти по такому ключу Mailtank')
        else:
            session['key'] = key.content
            db.session.add(key)
            db.session.commit()
            return redirect(url_for('key'))

    return render_template('index.html', form=form)


@app.route('/key/', methods=['GET', 'POST'])
def key():
    """Вьюшка, позволяющая менять настройки ключа от Mailtank в системе.
    Ожидает в POST параметрах 'key'"""
    key = AccessKey.query.filter_by(content=session['key']).first()
    form = KeyForm(request.form, obj=key)

    if form.validate_on_submit():
        form.populate_obj(key)
        db.session.add(key)
        db.session.commit()

    return render_template('key.html', key=key, form=form)
