import os
import re
import numpy as np
import tifffile
from scipy import ndimage
from skimage import measure, segmentation, filters, feature
import trimesh


def parse_imagej_metadata(tif):
    metadata = {'slices': 1, 'frames': 1, 'channels': 1}
    try:
        description = tif.pages[0].tags['ImageDescription'].value
        if isinstance(description, bytes):
            description = description.decode('utf-8')
        s_tk = re.search(r'slices=(\d+)', description)
        f_tk = re.search(r'frames=(\d+)', description)
        c_tk = re.search(r'channels=(\d+)', description)
        if s_tk: metadata['slices'] = int(s_tk.group(1))
        if f_tk: metadata['frames'] = int(f_tk.group(1))
        if c_tk: metadata['channels'] = int(c_tk.group(1))
    except Exception as e:
        print(f"Warning: Could not parse ImageJ metadata: {e}")
    return metadata


def process_pipeline(input_file_path, output_folder):
    filename = os.path.basename(input_file_path)
    exp_name = os.path.splitext(filename)[0]

    # --- KONFIGURACJA FOLDERÓW POD BLENDERA ---
    # Muszą pasować do INPUT_FOLDER w skryptach Blendera
    output_coat = os.path.join(output_folder, 'output-OBJ-coat', exp_name)
    output_nuclei = os.path.join(output_folder, 'output-OBJ-final', exp_name)

    os.makedirs(output_coat, exist_ok=True)
    os.makedirs(output_nuclei, exist_ok=True)

    print(f"--- Processing: {filename} ---")
    print(f"Output Coat: {output_coat}")
    print(f"Output Nuclei: {output_nuclei}")

    # Parametry
    CH_SEG = 0
    CH_ADD = 1
    COAT_THRESH_FACTOR = 0.10
    COAT_REDUCTION = 0.2

    TARGET_CH = 1
    MIN_NUCLEUS_VOL = 500
    NUCLEI_THRESH_FACTOR = 0.10
    NUCLEI_REDUCTION = 0.2
    SMOOTH_SIGMA = 1.5
    SMOOTH_MESH_SIGMA = 0.6

    BLENDER_SCALE = 0.02

    with tifffile.TiffFile(input_file_path) as tif:
        meta = parse_imagej_metadata(tif)
        volume_data = tif.asarray()

    dims = volume_data.shape
    num_t = meta['frames']
    num_z = meta['slices']
    num_ch = meta['channels']
    dim_y = dims[-2]
    dim_x = dims[-1]

    flat_data = volume_data.reshape(-1, dim_y, dim_x)
    global_center = np.array([dim_x, dim_y, num_z]) / 2.0

    begin_t = 1
    end_t = num_t - 1
    if end_t < begin_t:
        begin_t = 0
        end_t = num_t

    print(f"Dimensions: T={num_t}, Z={num_z}, CH={num_ch}, Y={dim_y}, X={dim_x}")
    print(f"Processing Frames: {begin_t + 1} to {end_t} (1-based)")

    # --- GŁÓWNA PĘTLA PO CZASIE ---
    for t in range(begin_t, end_t):
        frame_idx = t + 1
        print(f"  Frame T={frame_idx}...")

        vol_ch1 = np.zeros((num_z, dim_y, dim_x), dtype=np.float32)
        vol_ch2 = np.zeros((num_z, dim_y, dim_x), dtype=np.float32)

        for z in range(num_z):
            idx1 = t * num_z * num_ch + z * num_ch + CH_SEG
            idx2 = t * num_z * num_ch + z * num_ch + CH_ADD
            vol_ch1[z, :, :] = flat_data[idx1]
            if num_ch > 1:
                vol_ch2[z, :, :] = flat_data[idx2]

        if np.max(vol_ch1) == 0 and np.max(vol_ch2) == 0:
            print("    Skipping empty frame.")
            continue

        # ==========================================
        # CZĘŚĆ A: COAT (Otoczka) -> Pojedynczy plik OBJ
        # ==========================================
        vol_coat = vol_ch1 + vol_ch2
        vol_coat_smooth = ndimage.gaussian_filter(vol_coat, sigma=1.0)
        max_val_coat = np.max(vol_coat_smooth)

        if max_val_coat > 0:
            iso_level = max_val_coat * COAT_THRESH_FACTOR
            try:
                verts, faces, normals, values = measure.marching_cubes(vol_coat_smooth, iso_level)

                # Konwersja (Z, Y, X) -> (X, Y, Z)
                verts_xyz = np.zeros_like(verts)
                verts_xyz[:, 0] = verts[:, 2]  # X
                verts_xyz[:, 1] = verts[:, 1]  # Y
                verts_xyz[:, 2] = verts[:, 0]  # Z

                mesh = trimesh.Trimesh(vertices=verts_xyz, faces=faces)

                # Redukcja
                if COAT_REDUCTION < 1.0:
                    try:
                        target_faces = int(len(mesh.faces) * COAT_REDUCTION)
                        mesh = mesh.simplify_quadratic_decimation(target_faces)
                    except Exception:
                        pass

                        # Transformacje
                mesh.vertices -= global_center
                mesh.vertices *= BLENDER_SCALE

                # ZAPIS DO PLIKU OBJ (Dla skryptu objstoglbcoat.py)
                # Nazwa: np. Tile_1..._Frame_T005.obj
                coat_filename = f"{exp_name}_Frame_T{frame_idx:03d}.obj"
                mesh.export(os.path.join(output_coat, coat_filename))

            except Exception as e:
                print(f"    Error Coat: {e}")

        # ==========================================
        # CZĘŚĆ B: NUCLEI (Jądra) -> Jeden OBJ na klatkę (z wieloma obiektami w środku)
        # ==========================================
        vol_nuclei_raw = vol_ch2
        vol_nuc_smooth = ndimage.gaussian_filter(vol_nuclei_raw, sigma=SMOOTH_SIGMA)

        try:
            thresh_val = filters.threshold_otsu(vol_nuc_smooth)
            bw = vol_nuc_smooth > thresh_val
            distance = ndimage.distance_transform_edt(bw)
            coords = feature.peak_local_max(distance, min_distance=4, labels=bw)
            mask = np.zeros(distance.shape, dtype=bool)
            mask[tuple(coords.T)] = True
            markers, _ = ndimage.label(mask)
            labels = segmentation.watershed(-distance, markers, mask=bw)
            regions = measure.regionprops(labels)

            # Tworzymy scenę TYLKO dla tej klatki
            frame_scene = trimesh.Scene()
            nuclei_in_frame = 0

            for region in regions:
                if region.area < MIN_NUCLEUS_VOL:
                    continue

                min_z, min_y, min_x = region.bbox[0], region.bbox[1], region.bbox[2]
                max_z, max_y, max_x = region.bbox[3], region.bbox[4], region.bbox[5]

                crop_vol = vol_nuclei_raw[min_z:max_z, min_y:max_y, min_x:max_x]
                nucleus_vol = crop_vol * region.image
                nucleus_vol_smooth = ndimage.gaussian_filter(nucleus_vol, sigma=SMOOTH_MESH_SIGMA)

                max_n_val = np.max(nucleus_vol_smooth)
                if max_n_val == 0: continue

                iso_lev_nuc = max_n_val * NUCLEI_THRESH_FACTOR

                try:
                    v_n, f_n, _, _ = measure.marching_cubes(nucleus_vol_smooth, iso_lev_nuc)

                    v_xyz = np.zeros_like(v_n)
                    v_xyz[:, 0] = v_n[:, 2]
                    v_xyz[:, 1] = v_n[:, 1]
                    v_xyz[:, 2] = v_n[:, 0]

                    v_xyz[:, 0] += min_x
                    v_xyz[:, 1] += min_y
                    v_xyz[:, 2] += min_z

                    n_mesh = trimesh.Trimesh(vertices=v_xyz, faces=f_n)

                    if NUCLEI_REDUCTION < 1.0:
                        try:
                            target_f = int(len(n_mesh.faces) * NUCLEI_REDUCTION)
                            if target_f > 10:
                                n_mesh = n_mesh.simplify_quadratic_decimation(target_f)
                        except Exception:
                            pass

                    n_mesh.vertices -= global_center
                    n_mesh.vertices *= BLENDER_SCALE

                    # Dodajemy do sceny klatki.
                    # WAŻNE: W OBJ nazwa obiektu to node_name
                    n_node_name = f"Nucleus_{region.label}"
                    frame_scene.add_geometry(n_mesh, node_name=n_node_name)

                    nuclei_in_frame += 1

                except Exception:
                    pass

            # ZAPIS DO PLIKU OBJ (Dla skryptu objstoglbnuclei.py)
            if nuclei_in_frame > 0:
                nuclei_filename = f"{exp_name}_Frame_T{frame_idx:03d}.obj"
                frame_scene.export(os.path.join(output_nuclei, nuclei_filename))
                print(f"    Saved {nuclei_in_frame} nuclei to {nuclei_filename}")
            else:
                print("    No nuclei found.")

        except Exception as e:
            print(f"    Error processing nuclei seg: {e}")

    print("--- Finished ---")