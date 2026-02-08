from re import fullmatch
import eventlet
eventlet.monkey_patch()

import sys
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
# Upewnij się, że ten import działa u Ciebie
from formermatlabfunc import process_pipeline
from werkzeug.utils import secure_filename

app = Flask("Organoid Review")
CORS(app)

# Uruchamiamy SocketIO
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

user = os.environ.get('DB_USER', 'root')
password = os.environ.get('DB_PASSWORD', 'organoid123')
host = os.environ.get('DB_HOST', 'db')
dbname = os.environ.get('DB_NAME', 'organoid-db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}/{dbname}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

DATA_MOUNT_POINT = '/app/data'
TIFS_FOLDER = os.path.join(DATA_MOUNT_POINT, 'tiffs')
GLBS_FOLDER = os.path.join(DATA_MOUNT_POINT, 'glbs')
OBJS_FOLDER = os.path.join(DATA_MOUNT_POINT, 'objs')
MATLAB_FOLDER = os.path.join(DATA_MOUNT_POINT, 'matlab')
app.config['UPLOAD_FOLDER'] = TIFS_FOLDER

# BLENDER_COAT_SCRIPT_PATH = os.path.join(app.root_path, 'blender_scripts/ObjsToGlbCoat.py')
# BLENDER_NUCLEI_SCRIPT_PATH = os.path.join(app.root_path, 'blender_scripts/ObjsToGlbNuclei.py')
# BLENDER_EXEC = "/opt/blender/blender"

os.makedirs(TIFS_FOLDER, exist_ok=True)
os.makedirs(OBJS_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

SERVER_STATE = {
    "status": "waiting",  # waiting/processing
    "current_task": None
}

# 1. To jest punkt styku z Windows (zdefiniowany w docker-compose jako volume)
# Zmień mapowanie w docker-compose na: - ${DATA_PATH_HOST}:/app/data
# DATA_MOUNT_POINT = '/app/data'

# # 2. Teraz wszystkie inne foldery budujemy RELATYWNIE do tego punktu
# # Dzięki temu pliki wylądują na Twoim dysku F:

# # Jeśli Twój folder na dysku F zawiera bezpośrednio pliki .tif:
# TIFS_FOLDER = os.path.join({DATA_PATH_HOST}, 'tiffs')

# # Tutaj trafią wyniki (utworzą się fizyczne foldery na dysku F:)
# GLBS_FOLDER = os.path.join(DATA_MOUNT_POINT, 'glbs')
# OBJS_FOLDER = os.path.join(DATA_MOUNT_POINT, 'objs')
# PROCESSED_FOLDER = os.path.join(DATA_MOUNT_POINT, 'processed_data') # Dla numpy
# PLOT_FOLDER = os.path.join(DATA_MOUNT_POINT, 'matlab')

# # Foldery kodu (skrypty) zostają w app.root_path, bo one są częścią aplikacji, a nie danych
# MATLAB_FOLDER = os.path.join(app.root_path, 'matlab')
# # BLENDER_COAT_SCRIPT_PATH = os.path.join(app.root_path, 'blender_scripts/ObjsToGlbCoat.py')
# # BLENDER_NUCLEI_SCRIPT_PATH = os.path.join(app.root_path, 'blender_scripts/ObjsToGlbNuclei.py')
BLENDER_COAT_SCRIPT_PATH = os.path.join(app.root_path, 'blender_scripts/ObjsToGlbPack.py')
BLENDER_NUCLEI_SCRIPT_PATH = os.path.join(app.root_path, 'blender_scripts/ObjsToGlbPack.py')
BLENDER_EXEC = "/opt/blender/blender"

app.config['UPLOAD_FOLDER'] = TIFS_FOLDER

# Tworzenie folderów (żeby Python nie krzyczał, że ich nie ma)
os.makedirs(GLBS_FOLDER, exist_ok=True)
os.makedirs(OBJS_FOLDER, exist_ok=True)
# os.makedirs(PROCESSED_FOLDER, exist_ok=True)
# os.makedirs(PLOT_FOLDER, exist_ok=True)

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
    """
    Zapisuje logi. Używa sys.__stdout__ aby uniknąć RecursionError,
    gdy sys.stdout jest podmieniony przez SocketLogger.
    """
    try:
        # Piszemy bezpośrednio do prawdziwego strumienia wyjścia
        log_line = f"[{level}] (ID: {organoid_id}) {message}\n"
        sys.__stdout__.write(log_line) 
        sys.__stdout__.flush()
    except Exception:
        pass

    # 1. WebSocket
    try:
        socketio.emit('server_log', {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'level': level,
            'message': str(message),
            'organoid_id': organoid_id
        })
    except Exception as e:
        sys.__stdout__.write(f"Błąd WebSocket: {e}\n")
    
    socketio.emit('server_state', SERVER_STATE)

    # 2. Baza Danych
    try:
        # with app.app_context() jest kluczowe wewnątrz wątków
        with app.app_context():
            new_log = ProcessLog(level=level, message=str(message), organoid_id=organoid_id)
            db.session.add(new_log)
            db.session.commit()
    except Exception as e:
        sys.__stdout__.write(f"Błąd zapisu logu do DB: {e}\n")
        # Rollback jest ważny, żeby nie zblokować sesji DB
        try:
            with app.app_context():
                db.session.rollback()
        except:
            pass

def run_blender_subprocess(cmd, organoid_id, log_prefix="BLENDER"):
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                broadcast_log(line, log_prefix, organoid_id)
        process.stdout.close()
        return_code = process.wait()
        
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)
            
    except subprocess.CalledProcessError as e:
        broadcast_log(f"Błąd procesu (Exit Code {e.returncode})", "ERROR", organoid_id)
        raise e
    
def run_blender_conversion(input_folder_coat, output_file_coat, input_folder_nuclei, output_file_nuclei, organoid_id):
    broadcast_log(f"Rozpoczynam konwersję Blenderem: {input_folder_coat} -> {output_file_coat}", "INFO", organoid_id)
    
    cmd_coat = [
        BLENDER_EXEC, "--background", "--python", BLENDER_COAT_SCRIPT_PATH, "--",
        input_folder_coat, output_file_coat
    ]

    cmd_nuclei = [
        BLENDER_EXEC, "--background", "--python", BLENDER_NUCLEI_SCRIPT_PATH, "--",
        input_folder_nuclei, output_file_nuclei
    ]
    
    try:
        # Uruchamiamy Coat
        run_blender_subprocess(cmd_coat, organoid_id, "BLENDER_COAT")
        
        # Uruchamiamy Nuclei
        broadcast_log(f"Start Blendera: Nuclei -> {os.path.basename(output_file_nuclei)}", "INFO", organoid_id)
        run_blender_subprocess(cmd_nuclei, organoid_id, "BLENDER_NUCLEI")
        
        broadcast_log("Blender zakończył pracę sukcesem.", "SUCCESS", organoid_id)
    except subprocess.CalledProcessError as e:
        # Logowanie błędu jest już obsłużone w run_blender_subprocess
        pass

class SocketLogger:
    """
    Przechwytuje sys.stdout i wysyła go do broadcast_log.
    """
    def __init__(self, organoid_id):
        self.organoid_id = organoid_id

    def write(self, message):
        # Piszemy na prawdziwą konsolę (zeby nie stracić logów w dockerze)
        sys.__stdout__.write(message) 
        
        msg_clean = message.strip()
        if msg_clean:
            # Wysyłamy do WS i Bazy
            # Używamy flagi "PIPELINE" dla logów z funkcji przetwarzania
            broadcast_log(msg_clean, "PIPELINE", self.organoid_id)

    def flush(self):
        sys.__stdout__.flush()

def pipeline_wrapper(filename, organoid_id):
    with app.app_context():
        try:
            broadcast_log(f"Rozpoczynam zadanie dla: {filename}", "START", organoid_id)
            
            broadcast_log("Krok 1: Przetwarzanie obrazu...", "INFO", organoid_id)
            tiffs_path = os.path.join(TIFS_FOLDER, filename + ".tif")
            
            original_stdout = sys.stdout
            sys.stdout = SocketLogger(organoid_id)
            
            try:
                process_pipeline(tiffs_path, OBJS_FOLDER)
            except Exception as inner_e:
                sys.stdout = original_stdout 
                raise inner_e
            finally:
                sys.stdout = original_stdout
            
            coat_obj_folder = os.path.join(OBJS_FOLDER, "output-OBJ-coat", filename)
            nuclei_obj_folder = os.path.join(OBJS_FOLDER, "output-OBJ-final", filename)

            os.makedirs(os.path.join(GLBS_FOLDER, "outer"), exist_ok=True)
            os.makedirs(os.path.join(GLBS_FOLDER, "inner"), exist_ok=True)

            glb_output_path_coat = os.path.join(GLBS_FOLDER, "outer", filename + ".glb")
            glb_output_path_nuclei = os.path.join(GLBS_FOLDER, "inner", filename + ".glb")

            if not os.path.exists(coat_obj_folder):
                broadcast_log(f"Nie znaleziono folderu otoczki: {coat_obj_folder}", "ERROR", organoid_id)
                return
            
            broadcast_log("Przechodzę do konwersji 3D...", "INFO", organoid_id)
            
            run_blender_conversion(
                coat_obj_folder, 
                glb_output_path_coat, 
                nuclei_obj_folder, 
                glb_output_path_nuclei, 
                organoid_id
            )
            
            broadcast_log("Cały proces zakończony sukcesem.", "DONE", organoid_id)
            SERVER_STATE['status'] = 'waiting'
            SERVER_STATE['current_task'] = None
            organoid = Organoid.query.get(organoid_id)
            if organoid:
                organoid.is_initialized = True
                organoid.is_processed_glb = True
                db.session.commit()
                
                socketio.emit('organoid_update', {'id': organoid.id, 'isProcessedGlb': True})

        except Exception as e:
            broadcast_log(f"Błąd w pipeline: {str(e)}", "ERROR", organoid_id)
            import traceback
            sys.__stdout__.write(traceback.format_exc())

@app.route('/')
def index():
    return f"W bazie mamy {Organoid.query.count()} organoidow"

@app.route('/logs/recent', methods=['GET'])
def get_organoid_logs():
    logs = ProcessLog.query.order_by(ProcessLog.timestamp.desc()).limit(20).all()
    return jsonify([log.to_dict() for log in logs][::-1])

@app.route('/logs/<int:organoid_id>', methods=['GET'])
def get_specific_logs(organoid_id):
    logs = ProcessLog.query.filter_by(organoid_id=organoid_id).order_by(ProcessLog.timestamp.desc()).all()
    return jsonify([log.to_dict() for log in logs][::-1])

@app.route('/server/state', methods=['GET'])
def get_server_state():
    return jsonify(SERVER_STATE)

@app.route('/process/<int:organoid_id>/', methods=['POST'])
def trigger_processing(organoid_id):
    
    SERVER_STATE['status'] = 'processing'
    SERVER_STATE['current_task'] = organoid_id
    organoid = Organoid.query.get(organoid_id)
    if not organoid:
        return jsonify({'error': 'Nie znaleziono organoidu'}), 404

    thread = threading.Thread(
        target=pipeline_wrapper, 
        args=(organoid.filename, organoid.id)
    )
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
            safe_base_name = secure_filename(name.replace(" ", "_"))
            tiff_filename = safe_base_name + ".tif"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], tiff_filename)
            new_organoid = Organoid(name=name, filename=safe_base_name)
            db.session.add(new_organoid)
            db.session.commit()

            file.save(save_path)
            return jsonify({'message': 'Success', 'id': new_organoid.id}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Invalid data'}), 400

@app.route('/organoid/', methods=['GET'])
def get_organoids():
    organoids = Organoid.query.all()
    organoid_list = [{'id': o.id, 'name': o.name, 'isInitialized': o.is_initialized, 'isProcessedGlb': o.is_processed_glb, 'isInCurrentRd': o.is_in_current_rd} for o in organoids]
    return jsonify(organoid_list)

@app.route('/organoid/<int:organoid_id>/', methods=['GET'])
def get_organoid(organoid_id):
    organoid = Organoid.query.get(organoid_id)
    if not organoid: return jsonify({})
    return jsonify({'id': organoid.id, 'name': organoid.name, 'isInitialized': organoid.is_initialized, 'isProcessedGlb': organoid.is_processed_glb, 'isInCurrentRd': organoid.is_in_current_rd})
    
@app.route('/orthoSlices/<int:organoid_id>/', methods=['GET'])
def get_ortho_slices_image(organoid_id):
    organoid = Organoid.query.get(organoid_id)
    if not organoid: return jsonify({})
    file_path = os.path.join(OBJS_FOLDER, 'output-PLOTS', organoid.filename, 'Ortho_Slices.png')
    if not os.path.exists(file_path):
        return abort(404, description="File not found")
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))

@app.route('/lyapunov/<int:organoid_id>/', methods=['GET'])
def get_lyapunov_image(organoid_id):
    organoid = Organoid.query.get(organoid_id)
    if not organoid: return jsonify({})
    file_path = os.path.join(OBJS_FOLDER, 'output-PLOTS', organoid.filename, 'Lyapunov.png')
    if not os.path.exists(file_path):
        return abort(404, description="File not found")
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))

@app.route('/metrics/<int:organoid_id>/', methods=['GET'])
def get_metrics(organoid_id):
    organoid = Organoid.query.get(organoid_id)
    if not organoid: return jsonify({})
    file_path = os.path.join(OBJS_FOLDER, 'output-PLOTS', organoid.filename, 'metrics.json')
    if not os.path.exists(file_path):
        return abort(404, description="File not found")
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))

@app.route('/lyapunov_data/<int:organoid_id>/', methods=['GET'])
def get_lyapunov_data(organoid_id):
    organoid = Organoid.query.get(organoid_id)
    if not organoid: return jsonify({})
    file_path = os.path.join(OBJS_FOLDER, 'output-PLOTS', organoid.filename, 'lyapunov_data.json')
    if not os.path.exists(file_path):
        return abort(404, description="File not found")
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))

@app.route('/optimization_history/<int:organoid_id>/', methods=['GET'])
def get_optimization_history(organoid_id):
    organoid = Organoid.query.get(organoid_id)
    if not organoid: return jsonify({})
    file_path = os.path.join(OBJS_FOLDER, 'output-PLOTS', organoid.filename, 'optimization_history.json')
    if not os.path.exists(file_path):
        return abort(404, description="File not found")
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))

@app.route('/global_growth/<int:organoid_id>/', methods=['GET'])
def get_global_growth(organoid_id):
    organoid = Organoid.query.get(organoid_id)
    if not organoid: return jsonify({})
    file_path = os.path.join(OBJS_FOLDER, 'output-PLOTS', organoid.filename, 'global_growth.json')
    if not os.path.exists(file_path):
        return abort(404, description="File not found")
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))

@app.route('/organoid/<int:organoid_id>/<string:layer_type>', methods=['GET'])
def get_glb_file(organoid_id, layer_type):
    if layer_type not in ['inner', 'outer']:
        return abort(400, description="Type must be 'inner' or 'outer'")

    organoid = Organoid.query.get(organoid_id)
    if not organoid or not organoid.filename:
        return abort(404, description="No organoid found")

    directory = os.path.join(app.root_path, 'glbs', layer_type)
    try:
        return send_from_directory(directory, organoid.filename + '.glb')
    except FileNotFoundError:
        return abort(404, description="File not found")

@app.route('/organoid/process/', methods=['POST'])
def process_file():
    data = request.get_json(silent=True)
    if not data:
        data = request.form
    organoid_id = data.get('organoidId')
    return trigger_processing(organoid_id)


@app.route('/testprocess/', methods=['POST'])
def testprocess():
    base_folder = app.config['UPLOAD_FOLDER']
    input_file = os.path.join(base_folder, "Tile_1_processed_binned-2b.tif")
    process_pipeline(input_file, base_folder)

    return "Process started", 200

@socketio.on('connect')
def handle_connect():
    emit('server_state', SERVER_STATE)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("--- Baza danych zaktualizowana (db.create_all) ---")

    socketio.run(app, host='0.0.0.0', port=5000, debug=True)