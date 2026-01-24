import os
import pymysql
import pymysql.cursors
from flask import Flask, send_from_directory, abort, jsonify
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
    name = db.Column(db.String(255))
    filename = db.Column(db.String(255))

@app.route('/')
def index():
    return f"No witam cie czlowieku w bazie mamy {Organoid.query.count()} organoidow"

@app.route('/organoid/', methods=['GET'])
def get_organoids():
    organoids = Organoid.query.all()
    organoid_list = [{'id': o.id, 'name': o.name} for o in organoids]
    return jsonify(organoid_list)
    
@app.route('/organoid/<int:organoid_id>/<string:layer_type>', methods=['GET'])
def get_glb_file(organoid_id, layer_type):
    if layer_type not in ['inner', 'outer']:
        return abort(400, description="Type must be 'inner' or 'outer'")

    organoid = Organoid.query.get(organoid_id)
    if not organoid:
        return abort(404, description="No organoid for selected ID")

    if not organoid.filename:
        return abort(404, description="Organoid has no associated glb file")

    directory = os.path.join(app.root_path, 'glbs', layer_type)
    try:
        return send_from_directory(directory, organoid.filename + '.glb')
    except FileNotFoundError:
        return abort(404, description="Synchronization error: file not found on server")
    
if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)