from flask import Flask, request
import defusedxml.cElementTree as ET
import psycopg2
import re
import codecs

app = Flask(__name__, static_url_path='')

DB_HOST = "localhost"
DB_NAME = "PhoneAndSell"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_TABLE = "pis"
DB_TABLE_CS = "pis_cs"

xml = """
<?xml version="1.0" encoding="UTF-8"?><SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><SOAP-ENV:Body><ns1:procesaNotificacionSIS xmlns:ns1="InotificacionSIS" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><XML xsi:type="xsd:string"><![CDATA[<Message><Request Ds_Version=\'0.0\'><Fecha>16/02/2021</Fecha><Hora>17:05</Hora><Ds_SecurePayment>0</Ds_SecurePayment><Ds_Card_Country>999</Ds_Card_Country><Ds_Amount>1</Ds_Amount><Ds_Currency>978</Ds_Currency><Ds_Order>777777761</Ds_Order><Ds_MerchantCode>337884902</Ds_MerchantCode><Ds_Terminal>001</Ds_Terminal><Ds_Response>9915</Ds_Response><Ds_MerchantData></Ds_MerchantData><Ds_TransactionType>38</Ds_TransactionType><Ds_ConsumerLanguage>1</Ds_ConsumerLanguage><Ds_ErrorCode>SIS9915</Ds_ErrorCode><Ds_AuthorisationCode>      </Ds_AuthorisationCode></Request><Signature>HUv4m93fHHTCfaGwutupTIoof11BrG40GDAZ8vAjv34=</Signature></Message>]]></XML></ns1:procesaNotificacionSIS></SOAP-ENV:Body></SOAP-ENV:Envelope>
"""
# Regular expresions to prevent sql injections
VALID_IDENTIFIER = r'^[a-zA-Z_][a-zA-Z0-9_\$]*$'
VALID_VALUE = r'^[a-zA-Z0-9_/: \$]*$'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return "<RESPONSE>Send XML data</RESPONSE>"

    if request.method == 'POST':
    # if request.method == 'GET':

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


        data = request.data
        # data = xml
        if type(data) == bytes:
            data = request.data.decode('utf-8')

        declaration = data.find("?>")
        if declaration != -1:
            data = data[declaration + 2:]

        try:
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
                query = 'CREATE TABLE public."{0}" ({1}) WITH (OIDS=FALSE);'.format(DB_TABLE, tags)
                cursor.execute(query)
                conn.commit()

            # Check for duplicates in DB
            cond = "AND".join(["\"{0}\" = '{1}'".format(x.tag, x.text) for x in dataTag])
            query = 'SELECT * FROM "{0}" WHERE {1} LIMIT 1;'.format(DB_TABLE, cond)
            cursor.execute(query)
            res = cursor.fetchall()
            conn.commit()
            if len(res) != 0:
                return "<RESPONSE>Dataset already in database</RESPONSE>"



            tags = ",".join(['"{0}"'.format(x.tag) for x in dataTag])
            values = ",".join(["'{0}'".format(x.text) for x in dataTag])

            query = 'INSERT INTO "{0}"({1}) VALUES({2});'.format(DB_TABLE, tags, values)

            # Insert in DB
            cursor.execute(query)
            conn.commit()

        except:
            return "<RESPONSE>Invalid XML</RESPONSE>"
        return "<RESPONSE>OK</RESPONSE>"

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
        
        data = request.data;
        if type(data) == bytes:
            data = request.data.decode('utf-8')

        
        try:
            # Parse XML data
            dataTag = ET.fromstring(data)

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
            cursor.execute("select * from information_schema.tables where table_name=%s", (DB_TABLE_CS,))
            exists = bool(cursor.rowcount)
            if not exists:
                tags = ",".join(['"{0}" character varying'.format(x.tag) for x in dataTag])
                query = 'CREATE TABLE public."{0}" ({1}) WITH (OIDS=FALSE);'.format(DB_TABLE_CS, tags)
                cursor.execute(query)
                conn.commit()

            # Check for duplicates in DB
            cond = "AND".join(["\"{0}\" = '{1}'".format(x.tag, x.text) for x in dataTag])
            query = 'SELECT * FROM "{0}" WHERE {1} LIMIT 1;'.format(DB_TABLE_CS, cond)
            cursor.execute(query)
            res = cursor.fetchall()
            conn.commit()
            if len(res) != 0:
                return "<RESPONSE>Dataset already in database</RESPONSE>"



            tags = ",".join(['"{0}"'.format(x.tag) for x in dataTag])
            values = ",".join(["'{0}'".format(x.text) for x in dataTag])

            query = 'INSERT INTO "{0}"({1}) VALUES({2});'.format(DB_TABLE_CS, tags, values)

            # Insert in DB
            cursor.execute(query)
            conn.commit()

        except:
            return "<RESPONSE>Invalid XML</RESPONSE>"
        return "<RESPONSE>OK</RESPONSE>"


@app.route('/consulta', methods=['GET', 'POST'])
def consulta():
    if request.method == 'GET':  
        data = request.data
        # data = xml
        if type(data) == bytes:
            data = request.data.decode('utf-8')
      
        # Database connection
        # try:
        #     conn = psycopg2.connect(
        #             database=DB_NAME,
        #             user=DB_USER,
        #             password=DB_PASS,
        #             host=DB_HOST
        #         )
        #     cursor = conn.cursor()
        # except:
        #     return "<RESPONSE>Error connecting to database</RESPONSE>"
        
        
        # try:
        #     # Parse XML data
        #     # Check for duplicates in DB
        #     cond = "AND".join(["\"{0}\" = '{1}'".format(x.tag, x.text) for x in dataTag])
        #     query = 'SELECT * FROM "{0}" WHERE {1} LIMIT 1;'.format(DB_TABLE_CS, cond)
        #     cursor.execute(query)
        #     res = cursor.fetchall()
        #     conn.commit()
        #     if len(res) != 0:
        #         return "<RESPONSE>Dataset already in database</RESPONSE>"

        # except:
        #     return "<RESPONSE>Invalid XML</RESPONSE>"
        # return "<response>ok</response>"
        print(xml)
        return xml



if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8150)
    # app.run(debug=True)
