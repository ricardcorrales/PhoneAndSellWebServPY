from flask import Flask, request
import defusedxml.cElementTree as ET
import psycopg2
import re

app = Flask(__name__, static_url_path='')

DB_HOST = "localhost"
DB_NAME = "PhoneAndSell"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_TABLE = "pis"

# Regular expresions to prevent sql injections
VALID_IDENTIFIER = r'^[a-zA-Z_][a-zA-Z0-9_\$]*$'
VALID_VALUE = r'^[a-zA-Z0-9_ \$]*$'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return "<RESPONSE>Send XML data</RESPONSE>"

    if request.method == 'POST':
        
        # Database connection
        try:
            conn = psycopg2.connect(
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASS,
                    host=DB_HOST
                )
            cursor = conn.cursor()
        except:
            return "<RESPONSE>Error connecting to database</RESPONSE>"
        
        try:
            data = request.data;
            if type(data) == bytes:
                data = request.data.decode('utf-8')

            
            # Parse XML data
            dataTag = ET.fromstring(data)

            # Validate tag names
            for x in dataTag:
                if not re.match(VALID_IDENTIFIER, x.tag):
                    return "<RESPONSE>Invalid XML (Tag name)</RESPONSE>"

            # Validate tag values
            for x in dataTag:
                if not re.match(VALID_VALUE, x.text):
                    return "<RESPONSE>Invalid XML (Tag value)</RESPONSE>"

            # Create table if not exists
            cursor.execute("select * from information_schema.tables where table_name=%s", (DB_TABLE,))
            exists = bool(cursor.rowcount)
            if not exists:
                tags = ",".join(['"{0}" character varying'.format(x.tag) for x in dataTag])
                query = 'CREATE TABLE public."{0}" ({1}) WITH (OIDS=FALSE);'.format(DB_TABLE, tags)
                cursor.execute(query)
                conn.commit();

            # Check for duplicates in DB
            cond = "AND".join(["\"{0}\" = '{1}'".format(x.tag, x.text) for x in dataTag])
            query = 'SELECT * FROM "{0}" WHERE {1} LIMIT 1;'.format(DB_TABLE, cond)
            cursor.execute(query)
            res = cursor.fetchall()
            conn.commit();
            if len(res) != 0:
                return "<RESPONSE>Dataset already in database</RESPONSE>"



            tags = ",".join(['"{0}"'.format(x.tag) for x in dataTag])
            values = ",".join(["'{0}'".format(x.text) for x in dataTag])

            query = 'INSERT INTO "{0}"({1}) VALUES({2});'.format(DB_TABLE, tags, values)

            # Insert in DB
            cursor.execute(query)
            conn.commit();

        except:
            return "<RESPONSE>Invalid XML</RESPONSE>"
        return "<RESPONSE>OK</RESPONSE>"

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8150)
