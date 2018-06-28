from flask import Flask
from flask_admin import Admin,form
from flask_admin.model import BaseModelView
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from slugify import slugify
from datetime import datetime
from sqlalchemy.event import listens_for
from os.path import join,getsize
from os import remove
import soundfile
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'development key'

db = SQLAlchemy(app)

upload_path = '/opt/gigi/audiodbenv/static/uploads'

tags = db.Table('tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
    db.Column('clip_id', db.Integer, db.ForeignKey('clip.id'), primary_key=True)
)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    slug = db.Column(db.String(60),unique=True)

    def __repr__(self):
        return '<%r>' % self.slug


class Clip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(64),nullable=False)
    description = db.Column(db.UnicodeText, nullable=False)
    subtype = db.Column(db.String(15))
    samplerate = db.Column(db.Integer)
    channels = db.Column(db.Integer)
    fileformat = db.Column(db.String(10))
    rec_date = db.Column(db.DateTime)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    duration = db.Column(db.Float)
    length = db.Column(db.Float)
    path = db.Column(db.Unicode(128),nullable=False)
    notes = db.Column(db.UnicodeText)
    tags = db.relationship('Tag', secondary=tags, lazy='subquery',
        backref=db.backref('clips', lazy=True))


    def __repr__(self):
        return '<Clip %r>' % (self.name)

class TagModelView(ModelView):
    form_excluded_columns = ('slug')

    def on_model_change(self, form, model, is_created):
        if is_created and not model.slug:
            model.slug = str.lower(slugify(model.name))


# Administrative views
class ClipModelView(ModelView):
    form_excluded_columns = ('subtype','samplerate','channels','fileformat','length','bitwidth','duration','filename')
    # Override form field to use Flask-Admin FileUploadField
    form_overrides = {
        'path': form.FileUploadField
    }
    form_args = {
        'path': {
        'label': 'File',
        'base_path': upload_path,
        'allow_overwrite': False
        }
    }

    def on_model_change(self, form, model, is_created):
        if is_created and model.path and not model.subtype:
            f = join(upload_path,model.path)
            try:
                info = soundfile.info(f)
                print(form.data['path'].name)
            except:
                print('Unable to update clip info on {0}'.format(f))
                raise
            else:
                model.subtype = info.subtype
                model.channels = info.channels
                model.samplerate = info.samplerate
                model.fileformat = info.format
                model.duration = info.duration
                model.length = getsize(f)

@listens_for(Clip, 'after_delete')
def del_file(mapper, connection, target):
    if target.path:
        try:
            remove(join(upload_path, target.path))
        except OSError:
            # Don't care if was not deleted because it does not exist
            pass



admin = Admin(app, name='audiodb', template_mode='bootstrap3')
# Add administrative views here
admin.add_view(TagModelView(Tag, db.session))
admin.add_view(ClipModelView(Clip, db.session))

if __name__ == '__main__':
    #import os
    #if not os.path.exists(
    #    db.create_all()
    app.run()
