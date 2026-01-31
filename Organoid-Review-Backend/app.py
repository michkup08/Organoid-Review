import eventlet
eventlet.monkey_patch()

import os
import datetime
import threading
import subprocess
import pymysql
import pymysql.cursors
from flask import Flask, send_from_directory, abort, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from formermatlabfunc import process_pipeline
from werkzeug.utils import secure_filename

INTERNAL_DATA_FOLDER = os.environ.get('INPUT_FOLDER_INTERNAL', '/app/data')

app = Flask("Organoid Review")
CORS(app)

socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

user = os.environ.get('DB_USER', 'root')
password = os.environ.get('DB_PASSWORD', 'organoid123')
host = os.environ.get('DB_HOST', 'db')
dbname = os.environ.get('DB_NAME', 'organoid-review')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}/{dbname}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'tiffs')
MATLAB_FOLDER = os.path.join(app.root_path, 'matlab')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

SERVER_STATE = {
    "status": "waiting", # waiting/processing
    "current_task": None
}

class Organoid(db.Model):
    __tablename__ = 'organoids'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    filename = db.Column(db.String(255))
    is_initialized = db.Column(db.Boolean, default=False)
    is_processed_glb = db.Column(db.Boolean, default=False)
    is_in_current_rd = db.Column(db.Boolean, default=False)

class ProcessLog(db.Model):
    __tablename__ = 'process_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    level = db.Column(db.String(50)) # INFO, ERROR, MATLAB
    message = db.Column(db.Text)
    organoid_id = db.Column(db.Integer, db.ForeignKey('organoids.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'message': self.message,
            'organoid_id': self.organoid_id
        }

def broadcast_log(message, level="INFO", organoid_id=None):
    print(f"[{level}] {message}")
    
    socketio.emit('server_log', {
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'level': level,
        'message': message,
        'organoid_id': organoid_id
    })
    
    socketio.emit('server_state', SERVER_STATE)

    # W funkcji wątku użyjemy app.app_context(), tutaj zakładamy, że jest dostępne
    try:
        new_log = ProcessLog(level=level, message=message, organoid_id=organoid_id)
        db.session.add(new_log)
        db.session.commit()
    except Exception as e:
        print(f"Błąd zapisu logu do DB: {e}")
        db.session.rollback()

# def run_matlab_task(organoid_id, filename_base):
#     global SERVER_STATE
    
#     with app.app_context():
#         SERVER_STATE["status"] = "processing"
#         SERVER_STATE["current_task"] = f"Organoid ID: {organoid_id}"
#         broadcast_log(f"Rozpoczynam przetwarzanie MATLAB dla: {filename_base}", "INFO", organoid_id)

#         try:
#             # Konstrukcja komendy
            
#             cmd = f"cd('{MATLAB_FOLDER}'); try, modelCellsTo3D('{filename_base}'); catch e, disp(e.message); exit(1); end; exit(0);"
            
#             # Uruchomienie procesu
#             process = subprocess.Popen(
#                 ['matlab', '-batch', cmd],
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.STDOUT,
#                 text=True,
#                 bufsize=1
#             )

#             # Czytanie logów na żywo
#             for line in iter(process.stdout.readline, ''):
#                 line = line.strip()
#                 if line:
#                     # Wyślij każdy output MATLABA do websocket
#                     broadcast_log(line, "MATLAB", organoid_id)

#             process.stdout.close()
#             return_code = process.wait()

#             if return_code == 0:
#                 broadcast_log("Przetwarzanie MATLAB zakończone sukcesem.", "SUCCESS", organoid_id)
#                 # Opcjonalnie: zaktualizuj flagę w bazie
#                 org = Organoid.query.get(organoid_id)
#                 if org:
#                     org.is_processed_glb = True
#                     db.session.commit()
#             else:
#                 broadcast_log(f"MATLAB zakończył pracę z błędem (kod {return_code}).", "ERROR", organoid_id)

#         except Exception as e:
#             broadcast_log(f"Krytyczny błąd serwera podczas uruchamiania MATLABa: {str(e)}", "ERROR", organoid_id)
        
#         finally:
#             SERVER_STATE["status"] = "idle"
#             SERVER_STATE["current_task"] = None
#             broadcast_log("Serwer gotowy do dalszej pracy.", "INFO")

@app.route('/')
def index():
    return f"No witam cie czlowieku w bazie mamy {Organoid.query.count()} organoidow"

@app.route('/logs/recent', methods=['GET'])
def get_recent_logs():
    """Zwraca 10 ostatnich logów"""
    logs = ProcessLog.query.order_by(ProcessLog.timestamp.desc()).limit(10).all()
    # Odwracamy kolejność, żeby na froncie najnowsze były na dole (chyba że wolisz odwrotnie)
    return jsonify([log.to_dict() for log in logs][::-1])

@app.route('/server/state', methods=['GET'])
def get_server_state():
    """Zwraca aktualny stan (czy mieli dane)"""
    return jsonify(SERVER_STATE)

@app.route('/process/<int:organoid_id>', methods=['POST'])
def trigger_processing(organoid_id):
    if SERVER_STATE["status"] != "idle":
        return jsonify({'error': 'Serwer jest zajęty innym zadaniem'}), 429

    organoid = Organoid.query.get(organoid_id)
    if not organoid:
        return jsonify({'error': 'Nie znaleziono organoidu'}), 404

    # Uruchamiamy wątek w tle
    thread = threading.Thread(target=run_matlab_task, args=(organoid.id, organoid.filename))
    thread.start()

    return jsonify({'message': 'Proces uruchomiony w tle', 'organoid': organoid.name}), 202

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
            tiff_filename = safe_base_name + ".tif"
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

@socketio.on('connect')
def handle_connect():
    emit('server_state', SERVER_STATE)


@app.route('/process', methods=['POST'])
def process_file():
    data = request.json
    if not data:
        return jsonify({"error": "Brak danych JSON w żądaniu"}), 400

    file_path = data.get('file_path')

    if not file_path:
        return jsonify({"error": "Brakuje parametru 'file_path'"}), 400

    if not INTERNAL_DATA_FOLDER:
        return jsonify({"error": "Błąd konfiguracji serwera: INTERNAL_DATA_FOLDER is None"}), 500

    full_path = os.path.join(INTERNAL_DATA_FOLDER, file_path)

    if not os.path.exists(full_path):
        print(f"DEBUG: Szukałem pliku tutaj: {full_path}")
        return jsonify({"error": f"File not found: {file_path}"}), 404

    thread = threading.Thread(target=process_pipeline, args=(full_path, INTERNAL_DATA_FOLDER))
    thread.start()

    return jsonify({"message": "Processing started", "file": file_path})
    
if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)