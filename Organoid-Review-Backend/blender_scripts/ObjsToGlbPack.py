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

# OPTYMALIZACJA GEOMETRII
# 1.0 = 100% jakości (bez zmian)
# 0.4 = Zostawiamy 40% trójkątów (redukcja wagi o ~60%)
# Dla organicznych kształtów (organoidy) wartości 0.2 - 0.4 są zazwyczaj bezpieczne wizualnie.
DECIMATE_RATIO = 0.4

# Pozycje
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
    # Wyłączamy Undo dla oszczędności RAMu i szybkości
    bpy.context.preferences.edit.use_global_undo = False
    
    clean_scene()
    
    files = glob.glob(os.path.join(INPUT_FOLDER, FILE_EXT))
    files.sort(key=natural_sort_key)
    
    if not files:
        print("Brak plików!")
        return

    print(f"Tworzenie animacji z {len(files)} plików. Decymacja: {DECIMATE_RATIO}")
    
    # 1. IMPORT I OPTYMALIZACJA
    frame_containers = [] 
    
    for i, file_path in enumerate(files):
        bpy.ops.wm.obj_import(filepath=file_path)
        selected = bpy.context.selected_objects
        
        # --- BLOK OPTYMALIZACJI ---
        meshes = [obj for obj in selected if obj.type == 'MESH']
        for obj in meshes:
            bpy.context.view_layer.objects.active = obj
            
            # A. Decymacja (Zmniejszanie liczby trójkątów)
            if DECIMATE_RATIO < 1.0:
                mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
                mod.ratio = DECIMATE_RATIO
                bpy.ops.object.modifier_apply(modifier=mod.name)
            
            # B. Wygładzanie (Shade Smooth)
            # To nie tylko wygląda ładniej, ale zmniejsza rozmiar pliku GLB,
            # ponieważ wierzchołki są współdzielone (zamiast dublowane dla każdej ściany).
            bpy.ops.object.shade_smooth()
        # --------------------------

        # Tworzymy rodzica
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=HIDDEN_LOC)
        frame_parent = bpy.context.active_object
        frame_parent.name = f"Frame_{i}"
        
        # Przypisujemy dzieci
        for obj in selected:
            obj.parent = frame_parent
        
        frame_containers.append(frame_parent)
        bpy.ops.object.select_all(action='DESELECT')

    # 2. ANIMOWANIE
    total_frames = len(files)
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames - 1
    bpy.context.scene.render.fps = 10
    
    print("Generowanie kluczy lokalizacji...")
    
    for t in range(total_frames):
        for obj_idx, container in enumerate(frame_containers):
            if obj_idx == t:
                container.location = VISIBLE_LOC
            else:
                container.location = HIDDEN_LOC
            container.keyframe_insert(data_path="location", frame=t)

    # 3. INTERPOLACJA
    print("Ustawianie interpolacji Constant...")
    for container in frame_containers:
        if container.animation_data and container.animation_data.action:
            for fcurve in container.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'CONSTANT'

    # 4. FIX NLA
    print("Konwersja na paski NLA...")
    for container in frame_containers:
        if container.animation_data and container.animation_data.action:
            action = container.animation_data.action
            track = container.animation_data.nla_tracks.new()
            track.name = "VisibilityTrack"
            track.strips.new(action.name, 0, action)
            container.animation_data.action = None

    # 5. EKSPORT Z FILTROWANIEM DANYCH
    print(f"Eksport do {OUTPUT_FILE}...")
    
    bpy.ops.object.select_all(action='DESELECT')
    for container in frame_containers:
        container.select_set(True)
        for child in container.children:
            child.select_set(True)
            
    out_dir = os.path.dirname(OUTPUT_FILE)
    if not os.path.exists(out_dir): os.makedirs(out_dir)

    if OUTPUT_FILE.endswith(".glb"):
        bpy.ops.export_scene.gltf(
            filepath=OUTPUT_FILE,
            use_selection=True,
            export_format='GLB',
            export_animations=True,
            export_force_sampling=False, 
            export_nla_strips=True, 
            
            # --- AGRESYWNA CZYSTKA METADANYCH ---
            # To daje duży zysk bez utraty kształtu
            export_texcoords=False,   # Wyłączamy UV (nie masz tekstur obrazkowych)
            export_tangents=False,    # Wyłączamy styczne (nie masz normal map)
            export_colors=False,      # Wyłączamy kolory wierzchołków (chyba że ich używasz)
            export_normals=True,      # Zostawiamy (konieczne do oświetlenia!)
            # ------------------------------------
            
            export_materials='EXPORT'
        )
    print("SUKCES!")

if __name__ == "__main__":
    main()