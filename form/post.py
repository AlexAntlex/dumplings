from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, FileField


class PostForm(FlaskForm):
    text = TextAreaField()
    file_url = FileField()
    submit = SubmitField('Publicate')