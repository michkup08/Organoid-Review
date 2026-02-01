import bpy
import os
import glob
import re
import sys

# --- DIAGNOSTYKA I ARGUMENTY ---
print("-" * 50)
print("URUCHAMIAM SKRYPT BLENDERA")
print(f"Current working directory: {os.getcwd()}")
print(f"System args: {sys.argv}")

# Pobieranie argumentów po "--"
argv = sys.argv
if "--" in argv:
    args = argv[argv.index("--") + 1:]
else:
    args = []

print(f"Parsed args: {args}")

if len(args) < 2:
    print("BŁĄD: Nie podano ścieżek wejścia/wyjścia!")
    sys.exit(1)

INPUT_FOLDER = args[0]
OUTPUT_FILE = args[1]
FILE_EXT = "*.obj"

print(f"INPUT_FOLDER: '{INPUT_FOLDER}'")
print(f"OUTPUT_FILE: '{OUTPUT_FILE}'")

# --- SPRAWDZENIE ŚCIEŻEK ---
if not os.path.exists(INPUT_FOLDER):
    print(f"BŁĄD KRYTYCZNY: Folder wejściowy NIE ISTNIEJE: {INPUT_FOLDER}")
    # Wypiszmy zawartość folderu nadrzędnego, żeby zobaczyć gdzie jesteśmy
    parent_dir = os.path.dirname(INPUT_FOLDER)
    if os.path.exists(parent_dir):
        print(f"Zawartość folderu nadrzędnego ({parent_dir}): {os.listdir(parent_dir)}")
    else:
        print(f"Folder nadrzędny {parent_dir} też nie istnieje.")
    sys.exit(1)

# Sprawdzenie czy są pliki
files = glob.glob(os.path.join(INPUT_FOLDER, FILE_EXT))
print(f"Znaleziono {len(files)} plików .obj w folderze.")

if not files:
    print(f"BŁĄD: Folder {INPUT_FOLDER} jest pusty (brak .obj)!")
    print("Zawartość folderu:", os.listdir(INPUT_FOLDER))
    sys.exit(1)

# --- KONFIGURACJA ---
FPS = 10
VISIBLE_LOC = (0.0, 0.0, 0.0)
HIDDEN_LOC = (0.0, 0.0, -10000.0)

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def clean_scene():
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes: bpy.data.meshes.remove(block)
    for block in bpy.data.materials: bpy.data.materials.remove(block)
    for block in bpy.data.actions: bpy.data.actions.remove(block)
    bpy.ops.outliner.orphans_purge()

def main():
    try:
        clean_scene()
        files.sort(key=natural_sort_key)
        
        frame_containers = []
        
        # 1. IMPORT
        print("Rozpoczynam import...")
        for i, file_path in enumerate(files):
            bpy.ops.wm.obj_import(filepath=file_path)
            selected = bpy.context.selected_objects
            # ... (TUTAJ TWOJA LOGIKA NAPRAWY GEOMETRII - SKRÓCONA DLA CZYTELNOŚCI) ...
            
            # Grupowanie
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=HIDDEN_LOC)
            frame_parent = bpy.context.active_object
            frame_parent.name = f"Frame_{i}"
            for obj in selected:
                obj.parent = frame_parent
            frame_containers.append(frame_parent)
            bpy.ops.object.select_all(action='DESELECT')

        # 2. ANIMOWANIE
        print("Animowanie...")
        total_frames = len(files)
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = total_frames - 1
        bpy.context.scene.render.fps = FPS
        
        for t in range(total_frames):
            for obj_idx, container in enumerate(frame_containers):
                container.location = VISIBLE_LOC if obj_idx == t else HIDDEN_LOC
                container.keyframe_insert(data_path="location", frame=t)

        # 3. NLA
        print("Konwersja NLA...")
        for container in frame_containers:
            if container.animation_data and container.animation_data.action:
                action = container.animation_data.action
                track = container.animation_data.nla_tracks.new()
                track.strips.new(action.name, 0, action)
                container.animation_data.action = None

        # 4. EKSPORT
        output_dir = os.path.dirname(OUTPUT_FILE)
        if not os.path.exists(output_dir):
            print(f"Tworzę folder wyjściowy: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
            
        print(f"Zapisuję do: {OUTPUT_FILE}")
        
        # Selekcja wszystkiego do eksportu
        bpy.ops.object.select_all(action='SELECT')
        
        bpy.ops.export_scene.gltf(
            filepath=OUTPUT_FILE,
            use_selection=True,  # Ważne: eksportuje to co zaznaczone
            export_format='GLB',
            export_animations=True,
            export_nla_strips=True
        )
        
        if os.path.exists(OUTPUT_FILE):
            print(f"SUKCES! Plik utworzony: {os.path.getsize(OUTPUT_FILE)} bytes")
        else:
            print("BŁĄD: Blender zakończył export, ale pliku nie ma na dysku!")

    except Exception as e:
        import traceback
        print("KRYTYCZNY WYJĄTEK W BLENDERZE:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()