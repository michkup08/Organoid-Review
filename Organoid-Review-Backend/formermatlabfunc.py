import modelrdlinear
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


def center_volume(volume):
    mass_center = ndimage.center_of_mass(volume)
    if np.any(np.isnan(mass_center)):
        return (0, 0, 0)
    geo_center = np.array(volume.shape) / 2.0
    return geo_center - mass_center


def run_processing(input_file_path, output_base_folder):
    """ Generuje NPY (dane numeryczne) """
    filename = os.path.basename(input_file_path)
    exp_name = os.path.splitext(filename)[0]
    output_npy = os.path.join(output_base_folder, 'processed_data', exp_name)
    os.makedirs(output_npy, exist_ok=True)

    print(f"[PROCESSOR] Generating NPY for: {filename}")
    CH_SEG = 0;
    CH_ADD = 1

    with tifffile.TiffFile(input_file_path) as tif:
        meta = parse_imagej_metadata(tif)
        volume_data = tif.asarray()

    dims = volume_data.shape
    num_t = meta['frames'];
    num_z = meta['slices'];
    num_ch = meta['channels']
    dim_y = dims[-2];
    dim_x = dims[-1]
    flat_data = volume_data.reshape(-1, dim_y, dim_x)

    begin_t = 1;
    end_t = num_t - 1 if (num_t - 1) > 1 else num_t
    processed_frames = []

    for t in range(begin_t, end_t):
        frame_idx = t + 1
        vol_ch1 = np.zeros((num_z, dim_y, dim_x), dtype=np.float32)
        vol_ch2 = np.zeros((num_z, dim_y, dim_x), dtype=np.float32)

        for z in range(num_z):
            idx1 = t * num_z * num_ch + z * num_ch + CH_SEG
            idx2 = t * num_z * num_ch + z * num_ch + CH_ADD
            vol_ch1[z, :, :] = flat_data[idx1]
            if num_ch > 1: vol_ch2[z, :, :] = flat_data[idx2]

        if np.max(vol_ch1) == 0 and np.max(vol_ch2) == 0: continue

        vol_sum = vol_ch1 + vol_ch2
        shift_vector = center_volume(vol_sum)

        vol_coat_centered = ndimage.shift(vol_sum, shift_vector, order=1, mode='constant', cval=0)
        vol_nuclei_centered = ndimage.shift(vol_ch2, shift_vector, order=1, mode='constant', cval=0)

        coat_uint8 = np.clip(vol_coat_centered, 0, 255).astype(np.uint8)
        nuclei_uint8 = np.clip(vol_nuclei_centered, 0, 255).astype(np.uint8)

        np.save(os.path.join(output_npy, f"T{frame_idx:03d}_Coat.npy"), coat_uint8)
        np.save(os.path.join(output_npy, f"T{frame_idx:03d}_Nuclei.npy"), nuclei_uint8)
        processed_frames.append(frame_idx)

        if frame_idx % 10 == 0: print(f"  Processed NPY T={frame_idx}")

    return output_npy, processed_frames


def process_pipeline(input_file_path, output_folder):
    filename = os.path.basename(input_file_path)
    exp_name = os.path.splitext(filename)[0]

    # --- KROK 1: Generowanie NPY (Dane numeryczne) ---
    # Uruchamiamy to RAZ, przed wejściem w pętlę generowania grafiki
    npy_folder, frames = run_processing(input_file_path, output_folder)

    # Konfiguracja folderów wyjściowych OBJ
    output_coat = os.path.join(output_folder, 'output-OBJ-coat', exp_name)
    output_nuclei = os.path.join(output_folder, 'output-OBJ-final', exp_name)
    os.makedirs(output_coat, exist_ok=True)
    os.makedirs(output_nuclei, exist_ok=True)

    print(f"--- Processing Meshes for: {filename} ---")

    # Parametry (Takie jak miałeś w oryginale)
    COAT_THRESH_FACTOR = 0.10
    MIN_NUCLEUS_VOL = 500
    NUCLEI_THRESH_FACTOR = 0.10
    SMOOTH_SIGMA = 1.5
    SMOOTH_MESH_SIGMA = 0.6
    BLENDER_SCALE = 0.02

    # --- KROK 2: PĘTLA GENERUJĄCA OBJ (Tylko grafika) ---
    for frame_idx in frames:
        print(f"  Meshing Frame T={frame_idx}...")

        # Wczytujemy dane z NPY (szybciej niż z TIFF)
        coat_path = os.path.join(npy_folder, f"T{frame_idx:03d}_Coat.npy")
        nuclei_path = os.path.join(npy_folder, f"T{frame_idx:03d}_Nuclei.npy")

        # Jeśli plik nie istnieje (np. pusta klatka), pomiń
        if not os.path.exists(coat_path): continue

        vol_coat = np.load(coat_path)
        vol_nuclei = np.load(nuclei_path)

        # Obliczamy środek do skalowania
        dims = vol_coat.shape
        global_center = np.array([dims[2], dims[1], dims[0]]) / 2.0

        # --- A. COAT MESH ---
        try:
            vol_coat_smooth = ndimage.gaussian_filter(vol_coat.astype(float), sigma=1.0)
            max_val = np.max(vol_coat_smooth)

            if max_val > 0:
                iso_level = max_val * COAT_THRESH_FACTOR
                verts, faces, _, _ = measure.marching_cubes(vol_coat_smooth, iso_level)

                # Konwersja ZYX -> XYZ
                verts_xyz = verts[:, [2, 1, 0]]

                mesh = trimesh.Trimesh(vertices=verts_xyz, faces=faces)

                # Transformacje (bez redukcji w Pythonie)
                mesh.vertices -= global_center
                mesh.vertices *= BLENDER_SCALE

                mesh.export(os.path.join(output_coat, f"{exp_name}_Frame_T{frame_idx:03d}.obj"))
        except Exception:
            pass

        # --- B. NUCLEI MESH ---
        try:
            # Segmentacja
            vol_nuc_smooth = ndimage.gaussian_filter(vol_nuclei.astype(float), sigma=SMOOTH_SIGMA)
            thresh = filters.threshold_otsu(vol_nuc_smooth)
            bw = vol_nuc_smooth > thresh
            distance = ndimage.distance_transform_edt(bw)
            coords = feature.peak_local_max(distance, min_distance=4, labels=bw)
            mask = np.zeros(distance.shape, dtype=bool)
            mask[tuple(coords.T)] = True
            markers, _ = ndimage.label(mask)
            labels = segmentation.watershed(-distance, markers, mask=bw)
            regions = measure.regionprops(labels)

            frame_scene = trimesh.Scene()
            nuclei_in_frame = 0

            for region in regions:
                if region.area < MIN_NUCLEUS_VOL: continue

                min_z, min_y, min_x = region.bbox[:3]
                max_z, max_y, max_x = region.bbox[3:]

                crop = vol_nuclei[min_z:max_z, min_y:max_y, min_x:max_x] * region.image
                crop_smooth = ndimage.gaussian_filter(crop.astype(float), sigma=SMOOTH_MESH_SIGMA)

                if np.max(crop_smooth) == 0: continue

                try:
                    # Generowanie siatki jądra
                    iso_lev = np.max(crop_smooth) * NUCLEI_THRESH_FACTOR
                    v_n, f_n, _, _ = measure.marching_cubes(crop_smooth, iso_lev)

                    v_xyz = v_n[:, [2, 1, 0]]
                    v_xyz += [min_x, min_y, min_z]  # Przesunięcie do pozycji w klatce

                    n_mesh = trimesh.Trimesh(vertices=v_xyz, faces=f_n)

                    # Transformacje
                    n_mesh.vertices -= global_center
                    n_mesh.vertices *= BLENDER_SCALE

                    # Dodajemy do sceny (bez scalania w jedną siatkę - zachowujemy obiekty)
                    frame_scene.add_geometry(n_mesh, node_name=f"Nucleus_{region.label}")
                    nuclei_in_frame += 1
                except:
                    pass

            if nuclei_in_frame > 0:
                frame_scene.export(os.path.join(output_nuclei, f"{exp_name}_Frame_T{frame_idx:03d}.obj"))

        except Exception as e:
            print(f"    Error nuclei: {e}")

    # --- KROK 3: MODEL MATEMATYCZNY (Dopiero po zakończeniu wszystkich klatek!) ---
    print("\n=== STEP 3: Mathematical Modeling (RD) ===")
    modelrdlinear.run_model(npy_folder, output_folder, exp_name)

    print("--- All Pipelines Finished ---")