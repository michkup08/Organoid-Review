import os
import pymysql
import pymysql.cursors
from flask import Flask

app = Flask("Organoid Review")

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'db'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'organoid123'),
    'database': os.environ.get('DB_NAME', 'organoid-review'),
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

@app.route('/', methods=['GET'])
def hello_world():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() as version")
            result = cur.fetchone()
            db_version = result['version']
        conn.close()

        return f"<h1>Hello World!</h1><p style='color:green'>Połączenie z bazą udane. Host: {DB_CONFIG['host']}. Wersja MariaDB: <b>{db_version}</b></p>"

    except pymysql.MySQLError as e:
        return f"<h1>Hello World!</h1><p style='color:red'>Błąd połączenia z bazą ({DB_CONFIG['host']}): {e}</p>"

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)