from flask import Flask, request, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
import defusedxml.cElementTree as ET

import os

app = Flask(__name__, static_url_path='')

ALLOWED_EXTENSIONS = set(['xml'])

TMP_FILE = "./tmp.xml"
DB_TABLE = "Data"

#File extension checking
def allowed_filename(filename):
    filename = str.lower(filename)
    return '.' in filename and filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    data = ""

    if request.method == 'POST':
        submitted_file = request.files['file']
        if submitted_file and allowed_filename(submitted_file.filename):

            #TODO: If multiple uploads give a different filename

            submitted_file.save(TMP_FILE)

            try:
                root = ET.parse(TMP_FILE).getroot()
                dataTag = root.find("DATOSENTRADA")

                #TODO: Check for duplicates in DB
                
                
                # var1 = [x.tag for x in dataTag]
                # print("00:")
                # print(var1)
                # var1 = ['"{0}"'.format(x) for x in var1]
                # print("01:")
                # print(var1)
                # var1 = ",".join(var1)
                # print("02:")
                # print(var1)

                tags = ",".join(['"{0}"'.format(x.tag) for x in dataTag])
                values = ",".join(["'{0}'".format(x.text) for x in dataTag])
                query = "INSERT INTO \"{0}\"({1}) VALUES({2})".format(DB_TABLE, tags, values)
                data = query;

                #TODO: Insert in DB

            except:
                return "Wrong XML"
            
            os.unlink(TMP_FILE)
            
    return '''
        <!doctype html>
        <title>Upload XML</title>
        <h1>Upload XML</h1>
        <form action="" method=post enctype=multipart/form-data>
            <input type="file" name="file">
            <input type=submit value=Upload>
        </form>
        ''' + data


if __name__ == "__main__":
    app.run(debug=True)