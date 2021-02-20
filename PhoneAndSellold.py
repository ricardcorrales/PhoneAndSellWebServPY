from flask import Flask, request
import defusedxml.cElementTree as ET
import psycopg2
from psycopg2.extras import DictCursor
import re
import codecs
from collections import defaultdict
from waitress import serve

app = Flask(__name__, static_url_path='')

DB_HOST = "localhost"
DB_NAME = "PhoneAndSell"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_TABLE = "pis"
DB_TABLE_CS = "pis_cs"

# Update query settings
SEARCH = defaultdict(str)
SEARCH["Ds_Order"] = "DS_MERCHANT_ORDER"
SEARCH["Ds_MerchantCode"] = "DS_MERCHANT_MERCHANTCODE"
SEARCH["Ds_Terminal"] = "DS_MERCHANT_TERMINAL"
UPDATE = defaultdict(str)
UPDATE["Ds_Response"] = "DS_MERCHANT_ERROR"

# Initial values of CODES_TO_PRINT table creation
DEFAULT_VALID_TO_PRINT = ["0000", "9915"]


# GET VALID CODES TO PRINT
def validToPrint():
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
        return []

    # Create table if not exists
    cursor.execute("select * from information_schema.tables where table_name=%s", ("CODES_TO_PRINT",))
    exists = bool(cursor.rowcount)
    if not exists:
        query = 'CREATE TABLE public."CODES_TO_PRINT" ("CODE" character varying NOT NULL, CONSTRAINT pk PRIMARY KEY ("CODE")) WITH (OIDS=FALSE)'
        cursor.execute(query)
        conn.commit()

        # Insert defaults
        items = ','.join("('{0}')".format(x) for x in DEFAULT_VALID_TO_PRINT)
        cursor.execute('INSERT INTO "CODES_TO_PRINT" VALUES ' + items) 
        conn.commit()

    # Fetch code list
    cursor.execute('SELECT * FROM "CODES_TO_PRINT"')
    res = cursor.fetchall()
    return [x[0] for x in res]


# Regular expresions to prevent sql injections
VALID_IDENTIFIER = r'^[a-zA-Z_][a-zA-Z0-9_\$]*$'
VALID_VALUE = r'^[a-zA-Z0-9_/:, \$]*$'


# BANK ENDPOINT
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
            data = request.data
            if type(data) == bytes:
                data = request.data.decode('utf-8')

            declaration = data.find("?>")
            if declaration != -1:
                data = data[declaration + 2:]

            # Parse XML data
            dataTag = ET.fromstring(data)
            data = dataTag[0][0][0].text
            data = codecs.getdecoder("unicode_escape")(data)[0]
            dataTag = ET.fromstring(data)
            dataTag = dataTag[0]

            # Validate tag names
            for x in dataTag:
                if not re.match(VALID_IDENTIFIER, x.tag):
                    return "<RESPONSE>Invalid XML (Tag name)</RESPONSE>"

            # Validate tag values
            for x in dataTag:
                if x.text == None:
                    x.text = ""
                if not re.match(VALID_VALUE, x.text):
                    return "<RESPONSE>Invalid XML (Tag value)</RESPONSE>"

            # Create table if not exists
            cursor.execute("select * from information_schema.tables where table_name=%s", (DB_TABLE,))
            exists = bool(cursor.rowcount)
            if not exists:
                tags = ",".join(['"{0}" character varying'.format(x.tag) for x in dataTag])
                tags = tags + ',"timestamp" timestamp with time zone'
                query = 'CREATE TABLE public."{0}" ({1}) WITH (OIDS=FALSE)'.format(DB_TABLE, tags)
                cursor.execute(query)
                conn.commit()

            # Check for duplicates in DB
            cond = " AND ".join(["\"{0}\" = '{1}'".format(x.tag, x.text) for x in dataTag])
            query = 'SELECT * FROM "{0}" WHERE {1} LIMIT 1'.format(DB_TABLE, cond)
            cursor.execute(query)
            res = cursor.fetchall()

            if len(res) != 0:
                return "<RESPONSE>Dataset already in database</RESPONSE>"

            tags = ",".join(['"{0}"'.format(x.tag) for x in dataTag])
            values = ",".join(["'{0}'".format(x.text) for x in dataTag])

            # Insert in DB
            query = 'INSERT INTO "{0}"({1}, "timestamp") VALUES({2}, NOW()) '.format(DB_TABLE, tags, values)
            cursor.execute(query)
            conn.commit()

            # Update CS table
            search = []
            update = []
            for x in dataTag:
                match = UPDATE[x.tag]
                if match != "":
                    update.append("\"{0}\" = '{1}'".format(match, x.text))
                match = SEARCH[x.tag]
                if match != "":
                    search.append("\"{0}\" = '{1}'".format(match, x.text))
            search = " AND ".join(search)
            update = ",".join(update)

            query = 'UPDATE "{0}" SET {1} WHERE {2}'.format(DB_TABLE_CS, update, search)
            cursor.execute(query)
            conn.commit()

        except:
            return "<RESPONSE>Invalid XML</RESPONSE>"
        return "<RESPONSE>OK</RESPONSE>"


# C# ENDPOINT
@app.route('/cs', methods=['GET', 'POST'])
def cs():

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
            data = request.data
            if type(data) == bytes:
                data = request.data.decode('utf-8')

            # Parse XML data
            dataTag = ET.fromstring(data)
            for x in dataTag:
                if not re.match(VALID_IDENTIFIER, x.tag):
                    return "<RESPONSE>Invalid XML (Tag name)</RESPONSE>"
            # Validate tag values
            for x in dataTag:
                if x.text == None:
                    x.text = ""
                if not re.match(VALID_VALUE, x.text):
                    return "<RESPONSE>Invalid XML (Tag value)</RESPONSE>"

            # Create table if not exists
            cursor.execute("select * from information_schema.tables where table_name=%s", (DB_TABLE_CS,))
            exists = bool(cursor.rowcount)
            if not exists:
                tags = ",".join(['"{0}" character varying'.format(x.tag) for x in dataTag])
                tags = tags + ',"timestamp" timestamp with time zone'
                tags = tags + ',"printed" boolean DEFAULT false'
                query = 'CREATE TABLE public."{0}" ({1}) WITH (OIDS=FALSE)'.format(DB_TABLE_CS, tags)
                cursor.execute(query)
                conn.commit()

            # Check for duplicates in DB
            cond = " AND ".join(["\"{0}\" = '{1}'".format(x.tag, x.text) for x in dataTag])
            query = 'SELECT * FROM "{0}" WHERE {1} LIMIT 1'.format(DB_TABLE_CS, cond)
            cursor.execute(query)
            res = cursor.fetchall()
            conn.commit()
            if len(res) != 0:
                return "<RESPONSE>Dataset already in database</RESPONSE>"

            tags = ",".join(['"{0}"'.format(x.tag) for x in dataTag])
            values = ",".join(["'{0}'".format(x.text) for x in dataTag])

            # Insert in DB
            query = 'INSERT INTO "{0}"({1}, "timestamp") VALUES({2}, NOW())'.format(DB_TABLE_CS, tags, values)
            cursor.execute(query)
            conn.commit()

        except:
            return "<RESPONSE>Invalid XML</RESPONSE>"
        return "<RESPONSE>OK</RESPONSE>"


# GET LAST 2 DAYS LOGS
@app.route('/tail', methods=['GET'])
def tail():
    try:
        conn = psycopg2.connect(
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                host=DB_HOST
            )
        cursor = conn.cursor(cursor_factory = DictCursor)

        # Get las 2 days logs
        query = 'SELECT * FROM "{0}" WHERE "timestamp" > now() - interval \'2 days\''.format(DB_TABLE_CS)
        cursor.execute(query)
        res = cursor.fetchall()

        # Create response XML
        response = ""
        for row in res:
            line = ""
            for col in row.keys():
                line = line + "<{0}>{1}</{0}>".format(col, row[col])
            response = response + "<{0}>{1}</{0}>".format("LOG", line)

        return "<{0}>{1}</{0}>".format("RESPONSE", response)
    except:
        return "<RESPONSE>Error connecting to database</RESPONSE>"


# PRINT LIST
@app.route('/print', methods=['GET'])
def printList():
    conn = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST
        )
    cursor = conn.cursor(cursor_factory = DictCursor)

    # Get unprinted valid logs
    VALID_TO_PRINT = validToPrint()
    toPrint = ",".join(["'{0}'".format(x) for x in VALID_TO_PRINT])
    query = 'SELECT * FROM "{0}" WHERE "printed" = FALSE AND "DS_MERCHANT_ERROR" in ({1})'.format(DB_TABLE_CS, toPrint)
    cursor.execute(query)
    res = cursor.fetchall()

    # Update printed column
    query = 'UPDATE "{0}" SET "printed" = TRUE WHERE "printed" = FALSE AND "DS_MERCHANT_ERROR" in ({1})'.format(DB_TABLE_CS, toPrint)
    cursor.execute(query)
    conn.commit()

    # Create response XML
    response = ""
    for row in res:
        line = ""
        for col in row.keys():
            line = line + "<{0}>{1}</{0}>".format(col, row[col])
        response = response + "<{0}>{1}</{0}>".format("LOG", line)
    try:

        return "<{0}>{1}</{0}>".format("RESPONSE", response)
    except:
        return "<RESPONSE>Error connecting to database</RESPONSE>"


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8150)
