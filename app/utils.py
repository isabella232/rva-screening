# -*- coding: utf-8 -*-
import os
import json

from boto.s3.connection import S3Connection
from sqlalchemy import and_
from werkzeug import secure_filename
from werkzeug.datastructures import MultiDict

from flask import current_app, send_from_directory, session, abort
from flask.ext.login import login_user, current_user

from app import db, bcrypt
from app.models import AppUser, UnsavedForm


def send_document_image(file_name):
    """Serve an image file."""
    if current_app.config['SCREENER_ENVIRONMENT'] == 'prod':
        # conn = S3Connection(
        #     aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        #     aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
        # )
        # bucket = conn.get_bucket(current_app.config['S3_BUCKET_NAME'])
        # key = bucket.get_key(
        #    '/'.join([current_app.config['S3_FILE_UPLOAD_DIR'],
        #    file_name])
        # )

        # send_file(
        #     key.get_file(file_name)
        # )
        pass
    else:
        return send_from_directory(os.path.join(
            current_app.config['PROJECT_ROOT'],
            current_app.config['UPLOAD_FOLDER']),
            file_name
        )


def upload_file(file):
    """Upload a file to AWS or local upload folder."""
    if allowed_file(file.filename):
        file_name = secure_filename(file.filename)
        if current_app.config['SCREENER_ENVIRONMENT'] == 'prod':
            conn = S3Connection(
                aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY']
            )
            bucket = conn.get_bucket(current_app.config['S3_BUCKET_NAME'])
            _file = bucket.new_key('/'.join(
                [current_app.config['S3_FILE_UPLOAD_DIR'], file_name]
            ))
            _file.set_contents_from_file(file)
            _file.set_acl('public-read')
        else:
            file_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                file_name
            )
            file.save(file_path)

        return file_name


def allowed_file(filename):
    """Check that file extension is allowed."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1] in current_app.config.get('ALLOWED_EXTENSIONS')
    )


def translate_object(obj, language_code):
    """Replace string attributes of an object with translations from
    the database if available."""
    translations = next(
        (lang for lang in obj.translations if lang.language_code == language_code),
        None
    )
    if translations is not None:
        for key, value in translations.__dict__.iteritems():
            if (
                value is not None
                and not key.startswith('_')
                and hasattr(obj, key)
            ):
                setattr(obj, key, getattr(translations, key))
    return obj


def login_helper(user_email, password):
    user = AppUser.query.filter(AppUser.email == user_email).first()
    if user and bcrypt.check_password_hash(
        user.password.encode('utf8'),
        password
    ):
        user.authenticated = True
        db.session.add(user)
        db.session.commit()
        login_user(user)
        session.permanent = True
        return True
    else:
        return False


def get_unsaved_form(request, patient, page_name, form_class):
    """If the patient is logging back in after being automatically logged out
    due to inactivity, check whether there's unsaved form data we should restore.
    """
    if request.referrer and request.referrer.find('relogin'):
        unsaved_form = UnsavedForm.query.filter(and_(
            UnsavedForm.patient_id == patient.id,
            UnsavedForm.app_user_id == current_user.id,
            UnsavedForm.page_name.like('%' + page_name + '%')
        )).first()

        if unsaved_form:
            form_dict = {}
            for element in json.loads(unsaved_form.form_json):
                name = element['name']
                form_dict[name] = element['value']
            form_multidict = MultiDict(form_dict)
            form = form_class(formdata=form_multidict)

            # Once we've recreated the form, delete the temp data
            db.session.delete(unsaved_form)
            db.session.commit()

            return form
    return False


def check_patient_permission(patient_id):
    """If the current user is a patient account, check whether they're viewing
    the patient linked to their own account. If not, abort.
    """
    if current_user.is_patient_user() and current_user.patient_id != int(patient_id):
        abort(403)
    return

def days_from_today(field):
    '''Takes a python date object and returns days from today
    '''
    if isinstance(field, datetime.date):
        return (
            datetime.date(field.year, field.month, field.day) -
            datetime.date.today()
        ).days
    elif isinstance(field, datetime.datetime):
        field = field.replace(tzinfo=pytz.utc)
        return (
            datetime.datetime(field.year, field.month, field.day) -
            datetime.datetime.now(pytz.utc)
        ).days
    else:
        return field

def format_days_from_today(field):
    '''Uses days_from_today to build readable "X days ago"
    '''
    days = days_from_today(field)
    if days == 0:
        return 'Today'
    elif days == 1:
        return '{} day from now'.format(abs(days))
    elif days > 1:
        return '{} days from now'.format(abs(days))
    elif days == -1:
        return '{} day ago'.format(abs(days))
    else:
        return '{} days ago'.format(abs(days))
