from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_wtf import FlaskForm

class UploadForm(FlaskForm):
    file = FileField('Excel File', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Excel files only!')
    ])