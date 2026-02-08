import bpy
import os
import glob
import re
import sys

print("-" * 50)
print("URUCHAMIAM SKRYPT BLENDERA", flush=True)
print(f"Current working directory: {os.getcwd()}", flush=True)
print(f"System args: {sys.argv}", flush=True)

argv = sys.argv
if "--" in argv:
    args = argv[argv.index("--") + 1:]
else:
    args = []

print(f"Parsed args: {args}", flush=True)

if len(args) < 2:
    print("BŁĄD: Nie podano ścieżek wejścia/wyjścia!", flush=True)
    sys.exit(1)

INPUT_FOLDER = args[0]
OUTPUT_FILE = args[1]
FILE_EXT = "*.obj"

print(f"INPUT_FOLDER: '{INPUT_FOLDER}'")
print(f"OUTPUT_FILE: '{OUTPUT_FILE}'")

if not os.path.exists(INPUT_FOLDER):
    print(f"BŁĄD KRYTYCZNY: Folder wejściowy NIE ISTNIEJE: {INPUT_FOLDER}", flush=True)
    parent_dir = os.path.dirname(INPUT_FOLDER)
    if os.path.exists(parent_dir):
        print(f"Zawartość folderu nadrzędnego ({parent_dir}): {os.listdir(parent_dir)}", flush=True)
    else:
        print(f"Folder nadrzędny {parent_dir} nie istnieje.", flush=True)
    sys.exit(1)

files = glob.glob(os.path.join(INPUT_FOLDER, FILE_EXT))
print(f"Znaleziono {len(files)} plików .obj w folderze.", flush=True)

if not files:
    print(f"BŁĄD: Folder {INPUT_FOLDER} jest pusty (brak .obj)!", flush=True)
    print("Zawartość folderu:", os.listdir(INPUT_FOLDER), flush=True)
    sys.exit(1)

DECIMATE_RATIO = 0.4

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
    bpy.context.preferences.edit.use_global_undo = False
    
    clean_scene()
    
    files = glob.glob(os.path.join(INPUT_FOLDER, FILE_EXT))
    files.sort(key=natural_sort_key)
    
    if not files:
        print("Brak plików!", flush=True)
        return

    print(f"Tworzenie animacji z {len(files)} plików. Decymacja: {DECIMATE_RATIO}", flush=True)
    
    frame_containers = [] 
    
    for i, file_path in enumerate(files):
        bpy.ops.wm.obj_import(filepath=file_path)
        selected = bpy.context.selected_objects

        meshes = [obj for obj in selected if obj.type == 'MESH']
        for obj in meshes:
            bpy.context.view_layer.objects.active = obj
            
            if DECIMATE_RATIO < 1.0:
                mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
                mod.ratio = DECIMATE_RATIO
                bpy.ops.object.modifier_apply(modifier=mod.name)

            bpy.ops.object.shade_smooth()

        bpy.ops.object.empty_add(type='PLAIN_AXES', location=HIDDEN_LOC)
        frame_parent = bpy.context.active_object
        frame_parent.name = f"Frame_{i}"

        for obj in selected:
            obj.parent = frame_parent
        
        frame_containers.append(frame_parent)
        bpy.ops.object.select_all(action='DESELECT')

    total_frames = len(files)
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames - 1
    bpy.context.scene.render.fps = 10
    
    print("Generowanie kluczy lokalizacji...", flush=True)
    
    for t in range(total_frames):
        for obj_idx, container in enumerate(frame_containers):
            if obj_idx == t:
                container.location = VISIBLE_LOC
            else:
                container.location = HIDDEN_LOC
            container.keyframe_insert(data_path="location", frame=t)

    print("Ustawianie interpolacji Constant...", flush=True)
    for container in frame_containers:
        if container.animation_data and container.animation_data.action:
            for fcurve in container.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'CONSTANT'

    print("Konwersja na paski NLA...", flush=True)
    for container in frame_containers:
        if container.animation_data and container.animation_data.action:
            action = container.animation_data.action
            track = container.animation_data.nla_tracks.new()
            track.name = "VisibilityTrack"
            track.strips.new(action.name, 0, action)
            container.animation_data.action = None

    print(f"Eksport do {OUTPUT_FILE}...", flush=True)
    
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

            export_texcoords=False,
            export_tangents=False,
            export_colors=False,
            export_normals=True,
            
            export_materials='EXPORT'
        )
    print("SUKCES!", flush=True)

if __name__ == "__main__":
    main()