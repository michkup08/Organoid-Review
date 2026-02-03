import os
import glob
import numpy as np
import scipy.sparse as sp
from scipy.sparse import kron
from scipy.integrate import solve_ivp
from scipy.optimize import minimize
from scipy.ndimage import zoom
import matplotlib.pyplot as plt

# Ustawienie backendu matplotlib na 'Agg' (bezokienkowy) dla Dockera
import matplotlib

matplotlib.use('Agg')


def build_laplacian(Nx, Ny, Nz):
    """
    Tworzy macierz operatora Laplace'a (L_3D) używając iloczynów Kroneckera.
    Odpowiednik Matlabowego kron(Iz, kron(Ix, Dy1)) + ...
    """
    # 1D Laplacian dla X
    ex = np.ones(Nx)
    data_x = np.array([ex, -2 * ex, ex])
    diags_x = np.array([-1, 0, 1])
    Dx = sp.diags(data_x, diags_x, shape=(Nx, Nx), format='csc')
    # Warunki brzegowe (Neumann = 0 na krawędziach, aproksymacja jak w Matlabie)
    Dx[0, 1] = 2
    Dx[Nx - 1, Nx - 2] = 2

    # 1D Laplacian dla Y
    ey = np.ones(Ny)
    data_y = np.array([ey, -2 * ey, ey])
    diags_y = np.array([-1, 0, 1])
    Dy = sp.diags(data_y, diags_y, shape=(Ny, Ny), format='csc')
    Dy[0, 1] = 2
    Dy[Ny - 1, Ny - 2] = 2

    # 1D Laplacian dla Z
    ez = np.ones(Nz)
    data_z = np.array([ez, -2 * ez, ez])
    diags_z = np.array([-1, 0, 1])
    Dz = sp.diags(data_z, diags_z, shape=(Nz, Nz), format='csc')
    Dz[0, 1] = 2
    Dz[Nz - 1, Nz - 2] = 2

    # Macierze jednostkowe
    Ix = sp.eye(Nx)
    Iy = sp.eye(Ny)
    Iz = sp.eye(Nz)

    # L_3D = kron(Iz, kron(Ix, Dy)) + kron(Iz, kron(Dx, Iy)) + kron(Dz, kron(Ix, Iy))
    # Uwaga: Kolejność kron w Pythonie może być inna niż w Matlabie w zależności od spłaszczenia (C-order vs F-order)
    # Matlab (Column-major): Zewnętrzna pętla to X, potem Y, potem Z?
    # W Pythonie (C-major, domyślny reshape): Z, Y, X.

    # Python reshape order='C' (Z, Y, X):
    # L = D_z (x) I_y (x) I_x  +  I_z (x) D_y (x) I_x  +  I_z (x) I_y (x) D_x

    L_3D = kron(Dz, kron(Iy, Ix)) + kron(Iz, kron(Dy, Ix)) + kron(Iz, kron(Iy, Dx))
    return L_3D


def cost_function(params, dataset, L_3D, t_eval):
    """
    Funkcja kosztu do optymalizacji.
    """
    D = abs(params[0])
    Rho = params[1]

    # A = D * L + Rho * I
    # Tworzymy rzadką macierz systemu
    A = D * L_3D + Rho * sp.eye(L_3D.shape[0])

    total_err = 0

    for data_item in dataset:
        u0 = data_item['u0']
        real_data = data_item['data']  # (Time, Z, Y, X)

        # Rozwiązanie ODE
        # solve_ivp oczekuje funkcji f(t, y). Mnożenie macierzowe A @ y.
        def system_dynamics(t, y):
            return A @ y

        try:
            sol = solve_ivp(system_dynamics, [t_eval[0], t_eval[-1]], u0, t_eval=t_eval, method='RK45')

            # Oblicz błąd (MSE)
            # sol.y ma kształt (num_voxels, time_steps)
            if sol.status != 0: return 1e20

            sim_data = sol.y.T  # (Time, Voxels)

            # Spłaszczamy real_data do (Time, Voxels)
            real_flat = real_data.reshape(real_data.shape[0], -1)

            # Suma kwadratów różnic (ignorując NaN)
            err = np.nansum((sim_data - real_flat) ** 2)
            total_err += err

        except Exception:
            return 1e20

    return total_err


def run_model(input_npy_folder, output_base_folder, exp_name):
    print(f"[MODEL] Starting Linear RD Analysis for {exp_name}...")

    # Konfiguracja wyjścia
    output_plots = os.path.join(output_base_folder, 'output-PLOTS', exp_name)
    os.makedirs(output_plots, exist_ok=True)

    # 1. Wczytanie danych (NPY) i Downsampling
    # Celujemy w małą siatkę dla szybkości optymalizacji, np. 50x50x50
    TARGET_SHAPE = (50, 50, 50)  # (Z, Y, X)

    files = sorted(glob.glob(os.path.join(input_npy_folder, "*_Coat.npy")))
    if len(files) < 2:
        print("[MODEL] Not enough frames to model.")
        return

    # Wczytaj wszystkie klatki do jednej tablicy 4D: (Time, Z, Y, X)
    raw_frames = []
    print(f"[MODEL] Loading {len(files)} frames...")

    for fpath in files:
        vol = np.load(fpath).astype(float)
        # Downsampling (zoom)
        scale = np.array(TARGET_SHAPE) / np.array(vol.shape)
        vol_small = zoom(vol, scale, order=1)
        raw_frames.append(vol_small)

    data_4d = np.array(raw_frames)  # (Time, Z, Y, X)

    # Normalizacja do [0, 1]
    mx = np.max(data_4d)
    if mx > 0: data_4d /= mx

    # Przygotowanie struktury dataset (dla kompatybilności z funkcją kosztu)
    # W Matlabie była pętla po "Tiles", tu zakładamy jeden eksperyment = jeden Tile
    u0 = data_4d[0].flatten()  # Stan początkowy (t=0)
    dataset = [{'data': data_4d, 'u0': u0}]

    # Czas
    num_frames = data_4d.shape[0]
    t_eval = np.arange(num_frames)

    # 2. Budowa Operatora
    Nz, Ny, Nx = TARGET_SHAPE
    print("[MODEL] Building Laplacian...")
    L_3D = build_laplacian(Nx, Ny, Nz)

    # 3. Optymalizacja
    initial_params = [0.001, 0.002]  # [D, Rho]
    print("[MODEL] Optimizing parameters (this may take a while)...")

    res = minimize(
        cost_function,
        initial_params,
        args=(dataset, L_3D, t_eval),
        method='Nelder-Mead',
        options={'maxiter': 50, 'disp': True}  # Zmniejszamy iteracje dla testu
    )

    D_opt = abs(res.x[0])
    Rho_opt = res.x[1]
    print(f"[MODEL] Result: D={D_opt:.5f}, Rho={Rho_opt:.5f}")

    # 4. Symulacja końcowa z optymalnymi parametrami
    A_final = D_opt * L_3D + Rho_opt * sp.eye(L_3D.shape[0])

    sol = solve_ivp(lambda t, y: A_final @ y, [0, num_frames - 1], u0, t_eval=t_eval, method='RK45')
    sim_flat = sol.y.T  # (Time, Voxels)
    sim_4d = sim_flat.reshape(num_frames, Nz, Ny, Nx)

    # 5. Generowanie Wykresów (Zapis do plików)
    print("[MODEL] Generating plots...")

    # Wykres A: Global Intensity
    plt.figure(figsize=(10, 6))
    real_sum = np.sum(data_4d, axis=(1, 2, 3))
    sim_sum = np.sum(sim_4d, axis=(1, 2, 3))
    plt.plot(t_eval, real_sum, 'bo-', label='Real Data')
    plt.plot(t_eval, sim_sum, 'r--', label=f'Model (D={D_opt:.4f})')
    plt.title(f'Global Growth Dynamics - {exp_name}')
    plt.xlabel('Time (frames)')
    plt.ylabel('Total Intensity')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_plots, 'Global_Growth.png'))
    plt.close()

    # Wykres B: Przekroje (Orthogonal Slices) - ostatnia klatka
    mid_z, mid_y, mid_x = Nz // 2, Ny // 2, Nx // 2
    last_real = data_4d[-1]
    last_sim = sim_4d[-1]

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    # XY (Z=mid)
    axes[0, 0].imshow(last_real[mid_z, :, :], cmap='hot')
    axes[0, 0].set_title('Real XY')
    axes[1, 0].imshow(last_sim[mid_z, :, :], cmap='hot')
    axes[1, 0].set_title('Model XY')

    # XZ (Y=mid)
    axes[0, 1].imshow(last_real[:, mid_y, :], cmap='hot')
    axes[0, 1].set_title('Real XZ')
    axes[1, 1].imshow(last_sim[:, mid_y, :], cmap='hot')
    axes[1, 1].set_title('Model XZ')

    # YZ (X=mid)
    axes[0, 2].imshow(last_real[:, :, mid_x], cmap='hot')
    axes[0, 2].set_title('Real YZ')
    axes[1, 2].imshow(last_sim[:, :, mid_x], cmap='hot')
    axes[1, 2].set_title('Model YZ')

    plt.suptitle(f'Orthogonal Slices (Last Frame) - D={D_opt:.5f}, Rho={Rho_opt:.5f}')
    plt.savefig(os.path.join(output_plots, 'Ortho_Slices.png'))
    plt.close()

    # Wykres C: Residuals Histogram
    residuals = (data_4d - sim_4d).flatten()
    plt.figure(figsize=(10, 6))
    plt.hist(residuals, bins=50, color='gray', alpha=0.7, density=True)
    plt.title('Residuals Distribution')
    plt.xlabel('Error (Real - Model)')
    plt.grid(True)
    plt.savefig(os.path.join(output_plots, 'Residuals_Hist.png'))
    plt.close()

    print(f"[MODEL] Finished. Plots saved to {output_plots}")