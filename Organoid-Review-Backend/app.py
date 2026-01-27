import os
import pymysql
import pymysql.cursors
from flask import Flask, send_from_directory, abort, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask("Organoid Review")
CORS(app)

user = os.environ.get('DB_USER', 'root')
password = os.environ.get('DB_PASSWORD', 'organoid123')
host = os.environ.get('DB_HOST', 'db')
dbname = os.environ.get('DB_NAME', 'organoid-review')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}/{dbname}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'tiffs')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Upewniamy się, że folder istnieje
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Organoid(db.Model):
    __tablename__ = 'organoids'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    filename = db.Column(db.String(255))
    is_initialized = db.Column(db.Boolean, default=False)
    is_processed_glb = db.Column(db.Boolean, default=False)
    is_in_current_rd = db.Column(db.Boolean, default=False)


@app.route('/')
def index():
    return f"No witam cie czlowieku w bazie mamy {Organoid.query.count()} organoidow"

@app.route('/dataset/', methods=['POST'])
def upload_dataset():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    name = request.form.get('name')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and name:
        try:
            # Tu zapisz plik i dodaj wpis do bazy danych
            safe_base_name = secure_filename(name.replace(" ", "_"))
            tiff_filename = safe_base_name + ".tiff"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], tiff_filename)
            new_organoid = Organoid(name=name, filename=safe_base_name)
            db.session.add(new_organoid)
            db.session.commit()

            print(f"Dodano do bazy: {name} (ID: {new_organoid.id})")
            file.save(save_path)
            print(f"Otrzymano plik: {file.filename} dla zbioru: {name}")
            return jsonify({'message': 'Success'}), 200
        except Exception as e:
            db.session.rollback()
            print(f"Błąd: {str(e)}")
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Invalid data'}), 400

@app.route('/organoid/', methods=['GET'])
def get_organoids():
    organoids = Organoid.query.all()
    organoid_list = [{'id': o.id, 'name': o.name, 'isInitialized': o.is_initialized, 'isProcessedGlb': o.is_processed_glb, 'isInCurrentRd': o.is_in_current_rd} for o in organoids]
    return jsonify(organoid_list)

@app.route('/organoid/<int:organoid_id>/', methods=['GET'])
def get_organoid(organoid_id):
    organoids = Organoid.query.filter_by(id=organoid_id).all()
    organoid_list = [{'id': o.id, 'name': o.name, 'isInitialized': o.is_initialized, 'isProcessedGlb': o.is_processed_glb, 'isInCurrentRd': o.is_in_current_rd} for o in organoids]
    return jsonify(organoid_list[0] if organoid_list else {})
    
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