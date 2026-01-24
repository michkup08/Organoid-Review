import os
import pymysql
import pymysql.cursors
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask("Organoid Review")

user = os.environ.get('DB_USER', 'root')
password = os.environ.get('DB_PASSWORD', 'organoid123')
host = os.environ.get('DB_HOST', 'db')
dbname = os.environ.get('DB_NAME', 'organoid-review')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}/{dbname}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Organoid(db.Model):
    __tablename__ = 'organoids'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))

@app.route('/')
def index():
    return f"No witam cie czlowieku w bazie mamy {Organoid.query.count()} organoidow"

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)