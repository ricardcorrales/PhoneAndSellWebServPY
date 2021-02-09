from flask import Flask, request, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
import xml.etree.cElementTree as ET

import os

# import MySQLdb

app = Flask(__name__, static_url_path='')

UPLOAD_FOLDER = './'
ALLOWED_EXTENSIONS = set(['xml'])

#File extension checking
def allowed_filename(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    data = ""
    if request.method == 'POST':
        submitted_file = request.files['file']
        if submitted_file and allowed_filename(submitted_file.filename):
            filename = secure_filename(submitted_file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            submitted_file.save(path)

            data = "<hr>" +path + "<br>"
            root = ET.parse(path).getroot()
            for type_tag in root.findall('bar/type'):
                value = type_tag.get('foobar')
                data = data + type_tag.tag + " = " + value + "<br>"

            # return redirect(url_for('index', filename=filename))
    return '''
        <!doctype html>
        <title>Upload XML</title>
        <h1>Upload XML</h1>
        <form action="" method=post enctype="multipart/form-data">
            <input type="file" name="file">
            <input type=submit value=Upload>
        </form>
        ''' + data


if __name__ == "__main__":
    app.run(debug=True)