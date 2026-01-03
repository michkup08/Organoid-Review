import bpy
import os
import glob
import re

# --- KONFIGURACJA ---
INPUT_FOLDER = r"D:\pbl\organoid\output-OBJ-models\Tile_1_processed_binned-2b"
# Zapiszemy jako .glb (lepiej dla Reacta) lub .fbx
OUTPUT_FILE = r"D:\pbl\organoid\output-OBJ-models\Tile_1_processed_binned-2b\anim\animacja.glb"
FILE_EXT = "*.obj"

# Jak bardzo 'gęsta' ma być siatka bazowa?
# True = remeshujemy bazę, żeby miała dużo punktów do odwzorowania detali.
# False = zostawiamy topologię pierwszego pliku OBJ.
USE_REMESH = True
VOXEL_SIZE = 0.05  # Im mniejsza liczba, tym dokładniejszy (i cięższy) model


# --------------------

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]


def clean_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)


def main():
    clean_scene()

    files = glob.glob(os.path.join(INPUT_FOLDER, FILE_EXT))
    files.sort(key=natural_sort_key)

    if not files:
        print("Brak plików!")
        return

    print(f"Rozpoczynam morfowanie {len(files)} plików...")

    base_obj = None

    # --- KROK 1: Przygotowanie Bazy (Klatka 0) ---
    print(f"Importowanie bazy: {os.path.basename(files[0])}")
    bpy.ops.wm.obj_import(filepath=files[0])
    base_obj = bpy.context.selected_objects[0]
    base_obj.name = "MorphObject"

    # Opcjonalnie: Przeliczenie siatki (Remesh), aby ujednolicić gęstość
    if USE_REMESH:
        print("Remeshing bazy (Voxel)...")
        bpy.context.view_layer.objects.active = base_obj

        # Używamy modyfikatora Remesh Voxel dla równej topologii
        mod = base_obj.modifiers.new(name="Remesh", type='REMESH')
        mod.mode = 'VOXEL'
        mod.voxel_size = VOXEL_SIZE
        mod.adaptivity = 0.0

        # Aplikujemy modyfikator
        bpy.ops.object.modifier_apply(modifier="Remesh")

    # Dodaj podstawowy Shape Key
    base_obj.shape_key_add(name="Basis")
    bpy.ops.object.shade_smooth()

    # --- KROK 2: Pętla Shrinkwrap dla reszty plików ---

    # Ustawiamy parametry animacji
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = len(files) - 1

    for i, file_path in enumerate(files):
        # Pomijamy plik 0, bo on jest bazą, ale musimy go uwzględnić w animacji
        if i == 0:
            continue

        filename = os.path.basename(file_path)
        print(f"Przetwarzanie klatki {i}: {filename}")

        # Importuj cel (Target)
        bpy.ops.wm.obj_import(filepath=file_path)
        target_obj = bpy.context.selected_objects[0]  # Zakładamy, że to ten nowy

        # Upewnij się, że target jest 'wyczyszczony' (brak transformacji)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Aktywuj obiekt bazowy
        bpy.context.view_layer.objects.active = base_obj

        # Dodaj modyfikator Shrinkwrap
        sw_mod = base_obj.modifiers.new(name="Shrinkwrap", type='SHRINKWRAP')
        sw_mod.target = target_obj
        sw_mod.wrap_method = 'PROJECT'  # Często lepsze niż Nearest Surface Point dla skomplikowanych kształtów
        sw_mod.use_negative_direction = True
        sw_mod.use_positive_direction = True
        # Alternatywnie: sw_mod.wrap_method = 'NEAREST_SURFACEPOINT'

        # Zastosuj jako Shape Key
        bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False, modifier="Shrinkwrap")

        # Nowy Shape Key ma nazwę "Shrinkwrap", zmieniamy ją
        new_key = base_obj.data.shape_keys.key_blocks[-1]
        new_key.name = f"Frame_{i}"

        # Usuń obiekt target (już niepotrzebny, kształt przejęty)
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        bpy.ops.object.delete()

    # --- KROK 3: Animacja Shape Keys ---
    print("Tworzenie animacji...")
    key_blocks = base_obj.data.shape_keys.key_blocks

    for frame in range(len(files)):
        bpy.context.scene.frame_set(frame)

        for kb in key_blocks:
            if kb.name == "Basis": continue

            # Włączamy Shape Key tylko w odpowiedniej klatce
            # Płynność powstanie automatycznie pomiędzy klatkami dzięki interpolacji Blendera
            kb.value = 1.0 if kb.name == f"Frame_{frame}" else 0.0
            kb.keyframe_insert(data_path="value")

    # --- KROK 4: Eksport ---
    print(f"Eksport do {OUTPUT_FILE}...")
    bpy.ops.object.select_all(action='DESELECT')
    base_obj.select_set(True)

    if OUTPUT_FILE.endswith(".glb") or OUTPUT_FILE.endswith(".gltf"):
        bpy.ops.export_scene.gltf(
            filepath=OUTPUT_FILE,
            use_selection=True,
            export_format='GLB',
            export_morph=True,  # Ważne dla Shape Keys
            export_animations=True
        )
    elif OUTPUT_FILE.endswith(".fbx"):
        bpy.ops.export_scene.fbx(
            filepath=OUTPUT_FILE,
            use_selection=True,
            object_types={'MESH'},
            bake_anim=True,
            mesh_smooth_type='FACE'
        )

    print("Gotowe!")


if __name__ == "__main__":
    main()