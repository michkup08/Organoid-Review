import bpy
import os
import glob
import re

# --- KONFIGURACJA ---
INPUT_FOLDER = r"F:\pbl\output-OBJ-final\Tile_1_processed_binned-2b"
OUTPUT_FILE = r"F:\pbl\output-OBJ-final\Tile_1_processed_binned-2b\anim\nuclei.glb"
FILE_EXT = "*.obj"
FPS = 10

# Pozycje (WIDOCZNY = (0,0,0), UKRYTY = daleko w dół)
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
    clean_scene()
    
    files = glob.glob(os.path.join(INPUT_FOLDER, FILE_EXT))
    files.sort(key=natural_sort_key)
    
    if not files:
        print("Brak plików!")
        return

    print(f"Tworzenie animacji Teleportacji (Z-Hiding) z {len(files)} plików...")
    
    # 1. IMPORT
    frame_containers = [] 
    
    for i, file_path in enumerate(files):
        bpy.ops.wm.obj_import(filepath=file_path)
        selected = bpy.context.selected_objects
        
        # Tworzymy rodzica
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=HIDDEN_LOC)
        frame_parent = bpy.context.active_object
        frame_parent.name = f"Frame_{i}"
        
        # Przypisujemy dzieci
        for obj in selected:
            if obj.type == 'MESH':
                obj.parent = frame_parent
        
        frame_containers.append(frame_parent)
        bpy.ops.object.select_all(action='DESELECT')

    # 2. ANIMOWANIE
    total_frames = len(files)
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = total_frames - 1
    bpy.context.scene.render.fps = FPS
    
    print("Generowanie kluczy lokalizacji...")
    
    # Przechodzimy przez każdą klatkę (t)
    for t in range(total_frames):
        # Dla każdego obiektu (obj)
        for obj_idx, container in enumerate(frame_containers):
            
            # Jeśli to jest "jego czas":
            if obj_idx == t:
                container.location = VISIBLE_LOC
            # W przeciwnym razie:
            else:
                container.location = HIDDEN_LOC
            
            # Wstaw klucz LOKALIZACJI w klatce 't'
            container.keyframe_insert(data_path="location", frame=t)

    # 3. INTERPOLACJA CONSTANT
    print("Ustawianie interpolacji Constant...")
    for container in frame_containers:
        if container.animation_data and container.animation_data.action:
            for fcurve in container.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'CONSTANT'

    # 4. FIX NLA (BARDZO WAŻNE)
    # Bez tego GLTF często eksportuje tylko ostatni aktywny obiekt!
    print("Konwersja na paski NLA...")
    for container in frame_containers:
        if container.animation_data and container.animation_data.action:
            action = container.animation_data.action
            # Tworzymy ścieżkę NLA
            track = container.animation_data.nla_tracks.new()
            track.name = "VisibilityTrack"
            # Wrzucamy tam akcję
            track.strips.new(action.name, 0, action)
            # Odpinamy akcję z "aktywnego slotu", żeby leciała z NLA
            container.animation_data.action = None

    # 5. EKSPORT
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
            
            # Force Sampling = False, bo mamy klucze w każdej klatce + Constant
            export_force_sampling=False, 
            
            # NLA Strips = True (Kluczowe!)
            export_nla_strips=True, 
            
            export_materials='EXPORT'
        )
    print("SUKCES! (Metoda Teleportacji)")

if __name__ == "__main__":
    main()