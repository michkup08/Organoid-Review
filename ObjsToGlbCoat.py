import bpy
import os
import glob
import re

# --- KONFIGURACJA DLA OTOCZKI (COAT) ---
INPUT_FOLDER = r"F:\pbl\output-OBJ-coat\Tile_1_processed_binned-2b"
OUTPUT_FILE = r"F:\pbl\output-OBJ-coat\Tile_1_processed_binned-2b\anim\coat_anim.glb"
FILE_EXT = "*.obj"
FPS = 10

# Pozycje (WIDOCZNY = (0,0,0), UKRYTY = głęboko pod ziemią)
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
    
    # Szybkie czyszczenie
    for block in bpy.data.meshes: bpy.data.meshes.remove(block)
    for block in bpy.data.materials: bpy.data.materials.remove(block)
    for block in bpy.data.actions: bpy.data.actions.remove(block)
    bpy.ops.outliner.orphans_purge()

def main():
    # Wyłączamy Undo dla szybkości
    global_undo_state = bpy.context.preferences.edit.use_global_undo
    bpy.context.preferences.edit.use_global_undo = False
    
    try:
        clean_scene()
        
        files = glob.glob(os.path.join(INPUT_FOLDER, FILE_EXT))
        files.sort(key=natural_sort_key)
        
        if not files:
            print("Brak plików!")
            return

        print(f"Przetwarzanie OTOCZKI: {len(files)} klatek...")
        
        frame_containers = [] 
        
        # 1. IMPORT I NAPRAWA GEOMETRII
        for i, file_path in enumerate(files):
            print(f"Import klatki {i}/{len(files)}...")
            
            bpy.ops.wm.obj_import(filepath=file_path)
            selected = bpy.context.selected_objects
            meshes = [obj for obj in selected if obj.type == 'MESH']
            
            if meshes:
                # Naprawa geometrii (Batch Fix) - rozwiązuje problem "odwróconego cullingu"
                bpy.ops.object.select_all(action='DESELECT')
                for obj in meshes:
                    obj.select_set(True)
                
                bpy.context.view_layer.objects.active = meshes[0]
                
                # Reset transformacji
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
                
                # Naprawa normalnych (skierowanie na zewnątrz)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.normals_make_consistent(inside=False)
                bpy.ops.object.mode_set(mode='OBJECT')

            # Tworzenie rodzica (kontenera)
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=HIDDEN_LOC)
            frame_parent = bpy.context.active_object
            frame_parent.name = f"Frame_{i}"
            
            for obj in selected:
                obj.parent = frame_parent
            
            frame_containers.append(frame_parent)
            bpy.ops.object.select_all(action='DESELECT')

        # 2. ANIMOWANIE (Teleportacja)
        total_frames = len(files)
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = total_frames - 1
        bpy.context.scene.render.fps = FPS
        
        print("Generowanie animacji...")
        
        for t in range(total_frames):
            for obj_idx, container in enumerate(frame_containers):
                if obj_idx == t:
                    container.location = VISIBLE_LOC
                else:
                    container.location = HIDDEN_LOC
                container.keyframe_insert(data_path="location", frame=t)

        # 3. INTERPOLACJA & NLA
        print("Finalizacja danych...")
        for container in frame_containers:
            if container.animation_data and container.animation_data.action:
                action = container.animation_data.action
                
                # Constant Interpolation (Skokowa)
                for fcurve in action.fcurves:
                    for kf in fcurve.keyframe_points:
                        kf.interpolation = 'CONSTANT'
                
                # NLA Stash (Kluczowe dla Reacta)
                track = container.animation_data.nla_tracks.new()
                track.name = "VisTrack"
                track.strips.new(action.name, 0, action)
                container.animation_data.action = None

        # 4. EKSPORT
        print(f"Eksport do {OUTPUT_FILE}...")
        
        # --- FIX: TWORZENIE FOLDERU ---
        output_dir = os.path.dirname(OUTPUT_FILE)
        if not os.path.exists(output_dir):
            print(f"Tworzenie folderu: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        # ------------------------------
        
        bpy.ops.object.select_all(action='DESELECT')
        for container in frame_containers:
            container.select_set(True)
            for child in container.children:
                child.select_set(True)
                
        if OUTPUT_FILE.endswith(".glb"):
            bpy.ops.export_scene.gltf(
                filepath=OUTPUT_FILE,
                use_selection=True,
                export_format='GLB',
                export_animations=True,
                export_force_sampling=False, 
                export_nla_strips=True, 
                export_materials='EXPORT'
            )
        print("SUKCES!")

    finally:
        bpy.context.preferences.edit.use_global_undo = global_undo_state

if __name__ == "__main__":
    main()