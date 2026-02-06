import os
import glob
import json
import numpy as np
import scipy.sparse as sp
from scipy.sparse import kron
from scipy.integrate import solve_ivp
from scipy.optimize import minimize
from scipy.ndimage import zoom
from scipy.stats import pearsonr, spearmanr
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import cm
import matplotlib

# Ustawienie backendu matplotlib na 'Agg' (bezokienkowy) dla Dockera
matplotlib.use('Agg')


def build_laplacian(Nx, Ny, Nz):
    """
    Tworzy macierz operatora Laplace'a (L_3D) dla spłaszczenia typu C-order (Z, Y, X).
    Z - najwolniejszy indeks, X - najszybszy.
    L = Dz (x) Iy (x) Ix  +  Iz (x) Dy (x) Ix  +  Iz (x) Iy (x) Dx
    """
    # 1D Laplacian dla X
    ex = np.ones(Nx)
    data_x = np.array([ex, -2 * ex, ex])
    diags_x = np.array([-1, 0, 1])
    Dx = sp.diags(data_x, diags_x, shape=(Nx, Nx), format='csc')
    Dx[0, 1] = 2;
    Dx[Nx - 1, Nx - 2] = 2

    # 1D Laplacian dla Y
    ey = np.ones(Ny)
    data_y = np.array([ey, -2 * ey, ey])
    diags_y = np.array([-1, 0, 1])
    Dy = sp.diags(data_y, diags_y, shape=(Ny, Ny), format='csc')
    Dy[0, 1] = 2;
    Dy[Ny - 1, Ny - 2] = 2

    # 1D Laplacian dla Z
    ez = np.ones(Nz)
    data_z = np.array([ez, -2 * ez, ez])
    diags_z = np.array([-1, 0, 1])
    Dz = sp.diags(data_z, diags_z, shape=(Nz, Nz), format='csc')
    Dz[0, 1] = 2;
    Dz[Nz - 1, Nz - 2] = 2

    Ix = sp.eye(Nx)
    Iy = sp.eye(Ny)
    Iz = sp.eye(Nz)

    # Konstrukcja 3D (C-order: Z, Y, X)
    L_3D = kron(Dz, kron(Iy, Ix)) + kron(Iz, kron(Dy, Ix)) + kron(Iz, kron(Iy, Dx))
    return L_3D


def cost_function_structural(params, dataset, L_3D, t_eval, alpha=0.0):
    """
    Odpowiednik matlabowego cost3D_Isotropic_Structural.
    Jeśli alpha > 0, dodaje błąd gradientu (structural similarity).
    """
    D = abs(params[0])
    Rho = params[1]

    # A = D * L + Rho * I
    A = D * L_3D + Rho * sp.eye(L_3D.shape[0])

    total_err = 0
    # Pobieramy wymiary z pierwszego elementu datasetu
    # dataset[0]['data'] shape is (Time, Z, Y, X)
    _, Nz, Ny, Nx = dataset[0]['data'].shape

    for data_item in dataset:
        u0 = data_item['u0']
        real_data = data_item['data']  # (Time, Z, Y, X)

        try:
            # Rozwiązanie ODE: y' = Ay
            sol = solve_ivp(lambda t, y: A @ y, [t_eval[0], t_eval[-1]], u0, t_eval=t_eval, method='RK45')

            if sol.status != 0: return 1e20

            # sol.y shape: (num_voxels, num_steps) -> transpozycja na (Time, Voxels)
            sim_flat = sol.y.T

            # --- Obliczanie błędu ---
            # MSE
            real_flat = real_data.reshape(real_data.shape[0], -1)
            mse_err = np.nansum((sim_flat - real_flat) ** 2)

            grad_err = 0
            if alpha > 0:
                # Rekonstrukcja do 4D (Time, Z, Y, X) dla gradientów
                sim_4d = sim_flat.reshape(real_data.shape)

                # Obliczanie gradientów dla każdego kroku czasowego
                # np.gradient zwraca listę [grad_Z, grad_Y, grad_X] (zależnie od osi)
                # Iterujemy po czasie, żeby nie liczyć gradientu po osi czasu
                for t_idx in range(len(t_eval)):
                    vol_sim = sim_4d[t_idx]
                    vol_real = real_data[t_idx]

                    # Gradienty 3D
                    gs = np.gradient(vol_sim)  # [gz, gy, gx]
                    gr = np.gradient(vol_real)

                    mag_sim = np.sqrt(gs[0] ** 2 + gs[1] ** 2 + gs[2] ** 2)
                    mag_real = np.sqrt(gr[0] ** 2 + gr[1] ** 2 + gr[2] ** 2)

                    grad_err += np.nansum((mag_sim - mag_real) ** 2)

            total_err += mse_err + (alpha * grad_err)

        except Exception:
            return 1e20

    return total_err


def calculate_metrics(y_real, y_model, A_final, u0, t_eval, n_params=2):
    """
    Oblicza RMSE, R2, AIC, Lyapunov, Pearson, Spearman, RESET.
    """
    # 1. Podstawowe statystyki
    residuals = y_real - y_model
    sse = np.sum(residuals ** 2)
    n_points = len(y_real)
    rmse = np.sqrt(sse / n_points)

    sst = np.sum((y_real - np.mean(y_real)) ** 2)
    r2 = 1 - (sse / sst) if sst != 0 else 0

    # AIC: n * log(SSE/n) + 2k
    aic = n_points * np.log(sse / n_points) + 2 * n_params if sse > 0 else np.inf

    # 2. Korelacje
    r_pearson, _ = pearsonr(y_real, y_model)
    r_spearman, _ = spearmanr(y_real, y_model)

    # 3. RESET Proxy (korelacja reszt z kwadratem modelu)
    y_mod2 = y_model ** 2
    reset_corr, _ = pearsonr(residuals, y_mod2)

    # 4. Wykładnik Lyapunova (Perturbacja)
    epsilon = 1e-6
    u0_pert = u0 + epsilon * np.random.rand(len(u0))

    # Symulacja zaburzona
    try:
        sol_pert = solve_ivp(lambda t, y: A_final @ y, [t_eval[0], t_eval[-1]], u0_pert, t_eval=t_eval, method='RK45')
        # Symulacja oryginalna (trzeba przeliczyć lub przekazać, tu liczymy dla pewności kształtów)
        sol_orig = solve_ivp(lambda t, y: A_final @ y, [t_eval[0], t_eval[-1]], u0, t_eval=t_eval, method='RK45')

        # Obliczanie dystansu w czasie
        # sol.y shape (voxels, time) -> transponujemy do (time, voxels)
        U_sim = sol_orig.y.T
        U_pert = sol_pert.y.T

        dists = np.linalg.norm(U_sim - U_pert, axis=1)

        # Dopasowanie wykładnicze: log(dist) ~ lambda * t + b
        # Unikamy log(0) dodając eps
        log_dists = np.log(dists + np.finfo(float).eps)
        coeffs = np.polyfit(t_eval, log_dists, 1)
        lambda_lyap = coeffs[0]

    except Exception:
        lambda_lyap = np.nan
        dists = np.zeros(len(t_eval))
        coeffs = [0, 0]

    return {
        'RMSE': rmse, 'R2': r2, 'AIC': aic,
        'Lyapunov': lambda_lyap, 'Pearson': r_pearson,
        'Spearman': r_spearman, 'RESET': reset_corr,
        'Dists': dists, 'Lyap_Coeffs': coeffs
    }


def run_model(input_npy_folder, output_base_folder, exp_name):
    print(f"[MODEL] Starting Linear RD Analysis (MATLAB-Style) for {exp_name}...")

    # Konfiguracja wyjścia
    output_plots = os.path.join(output_base_folder, 'output-PLOTS', exp_name)
    os.makedirs(output_plots, exist_ok=True)

    # 1. Wczytanie danych
    TARGET_SHAPE = (50, 50, 50)
    files = sorted(glob.glob(os.path.join(input_npy_folder, "*_Coat.npy")))
    if len(files) < 2:
        print("[MODEL] Not enough frames.")
        return

    raw_frames = []
    print(f"[MODEL] Loading {len(files)} frames...")
    for fpath in files:
        vol = np.load(fpath).astype(float)
        scale = np.array(TARGET_SHAPE) / np.array(vol.shape)
        vol_small = zoom(vol, scale, order=1)
        raw_frames.append(vol_small)

    data_4d = np.array(raw_frames)
    mx = np.max(data_4d)
    if mx > 0: data_4d /= mx

    u0 = data_4d[0].flatten()
    dataset = [{'data': data_4d, 'u0': u0, 'ID': exp_name}]
    num_frames = data_4d.shape[0]
    t_eval = np.arange(num_frames)

    # 2. Budowa Operatora
    Nz, Ny, Nx = TARGET_SHAPE
    print(f"[MODEL] Building Laplacian {Nx}x{Ny}x{Nz}...")
    L_3D = build_laplacian(Nx, Ny, Nz)

    # 3. Optymalizacja z Callbackiem (JSON: Optimization History)
    initial_params = [0.001, 0.002]
    alpha_struct = 8.0

    # --- NOWOŚĆ: Przechowywanie historii optymalizacji ---
    opt_history = {
        'iteration': [],
        'D': [],
        'Rho': []
    }

    def optimization_callback(xk):
        """Callback wywoływany po każdej iteracji Nelder-Mead"""
        iter_idx = len(opt_history['iteration']) + 1
        opt_history['iteration'].append(iter_idx)
        opt_history['D'].append(float(abs(xk[0])))  # json.dump nie lubi numpy types
        opt_history['Rho'].append(float(xk[1]))
        print(f"   Iter {iter_idx}: D={abs(xk[0]):.5f}, Rho={xk[1]:.5f}")

    print("[MODEL] Optimizing (Nelder-Mead)...")

    res = minimize(
        cost_function_structural,
        initial_params,
        args=(dataset, L_3D, t_eval, alpha_struct),
        method='Nelder-Mead',
        callback=optimization_callback,  # <--- Podpięcie callbacka
        options={'maxiter': 100, 'disp': True, 'xatol': 1e-4, 'fatol': 1e-2}
    )

    D_opt = abs(res.x[0])
    Rho_opt = res.x[1]
    print(f"[MODEL] Result: D={D_opt:.5f}, Rho={Rho_opt:.5f}")

    # 4. Symulacja Finalna
    A_final = D_opt * L_3D + Rho_opt * sp.eye(L_3D.shape[0])
    sol = solve_ivp(lambda t, y: A_final @ y, [0, num_frames - 1], u0, t_eval=t_eval, method='RK45')

    sim_flat = sol.y.T
    sim_4d = sim_flat.reshape(num_frames, Nz, Ny, Nx)

    # 5. Walidacja i Metryki
    print("[MODEL] Calculating Validation Metrics...")
    y_real = data_4d.flatten()
    y_model = sim_4d.flatten()
    metrics = calculate_metrics(y_real, y_model, A_final, u0, t_eval)

    # --- GENEROWANIE JSONÓW DLA REACT ---

    print("[MODEL] Generating JSON data for React...")

    # A. Historia Optymalizacji
    with open(os.path.join(output_plots, 'optimization_history.json'), 'w') as f:
        json.dump(opt_history, f, indent=2)

    # B. Dane Lyapunova (Reakcja/Stabilność w czasie)
    lyap_trend = np.polyval(metrics['Lyap_Coeffs'], t_eval)
    lyapunov_data = {
        'time': t_eval.tolist(),
        'log_distance': np.log(metrics['Dists'] + np.finfo(float).eps).tolist(),
        'trend_line': lyap_trend.tolist(),
        'lambda': float(metrics['Lyapunov'])
    }
    with open(os.path.join(output_plots, 'lyapunov_data.json'), 'w') as f:
        json.dump(lyapunov_data, f, indent=2)

    # C. Globalna Intensywność (Total Growth) - bardzo przydatne do wizualizacji
    real_sum = np.sum(data_4d, axis=(1, 2, 3))
    sim_sum = np.sum(sim_4d, axis=(1, 2, 3))
    growth_data = {
        'time': t_eval.tolist(),
        'real_total_intensity': real_sum.tolist(),
        'model_total_intensity': sim_sum.tolist()
    }
    with open(os.path.join(output_plots, 'global_growth.json'), 'w') as f:
        json.dump(growth_data, f, indent=2)

    # D. Metryki skalarne (Metrics)
    metrics_json = {
        'RMSE': float(metrics['RMSE']),
        'R2': float(metrics['R2']),
        'AIC': float(metrics['AIC']),
        'Lyapunov': float(metrics['Lyapunov']),
        'Pearson': float(metrics['Pearson']),
        'Spearman': float(metrics['Spearman']),
        'RESET': float(metrics['RESET']),
        'D_opt': float(D_opt),
        'Rho_opt': float(Rho_opt)
    }
    with open(os.path.join(output_plots, 'metrics.json'), 'w') as f:
        json.dump(metrics_json, f, indent=2)

    # --- ZAPIS WYKRESÓW STATYCZNYCH (PNG) ---
    # (Zachowujemy dla kompatybilności wstecznej lub szybkiego podglądu)

    # Wykres Lyapunova (PNG)

    plt.figure(figsize=(8, 6))
    plt.plot(t_eval, np.log(metrics['Dists'] + np.finfo(float).eps), 'b-o', label='Log(Distance)')
    plt.plot(t_eval, lyap_trend, 'r--', label=f'Trend (Lambda={metrics["Lyapunov"]:.4f})')
    plt.title(f'Perturbation Dynamics (Lyapunov)\nLambda = {metrics["Lyapunov"]:.4f}')
    plt.xlabel('Time')
    plt.ylabel('log(Trajectory Distance)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_plots, 'Lyapunov.png'))
    plt.close()

    # Wykres Ortho Slices (PNG) - bez zmian
    mid_z, mid_y, mid_x = Nz // 2, Ny // 2, Nx // 2
    vol_real = data_4d[-1]
    vol_sim = sim_4d[-1]
    fig, axes = plt.subplots(3, 3, figsize=(12, 12))
    # ... (kod rysowania wykresów ortho slices jak wcześniej) ...
    # Dla skrótu wklejam tylko logikę zapisu, bo reszta jest długa:
    im1 = axes[0, 0].imshow(vol_real[mid_z, :, :], cmap='hot');
    axes[0, 0].set_title('XY Real')
    im2 = axes[0, 1].imshow(vol_sim[mid_z, :, :], cmap='hot');
    axes[0, 1].set_title('XY Model')
    im3 = axes[0, 2].imshow(vol_real[mid_z] - vol_sim[mid_z], cmap='jet');
    axes[0, 2].set_title('XY Diff')
    plt.colorbar(im3, ax=axes[0, 2])
    im4 = axes[1, 0].imshow(vol_real[:, mid_y, :], cmap='hot');
    axes[1, 0].set_title('XZ Real')
    im5 = axes[1, 1].imshow(vol_sim[:, mid_y, :], cmap='hot');
    axes[1, 1].set_title('XZ Model')
    im6 = axes[1, 2].imshow(vol_real[:, mid_y, :] - vol_sim[:, mid_y, :], cmap='jet');
    axes[1, 2].set_title('XZ Diff')
    plt.colorbar(im6, ax=axes[1, 2])
    im7 = axes[2, 0].imshow(vol_real[:, :, mid_x], cmap='hot');
    axes[2, 0].set_title('YZ Real')
    im8 = axes[2, 1].imshow(vol_sim[:, :, mid_x], cmap='hot');
    axes[2, 1].set_title('YZ Model')
    im9 = axes[2, 2].imshow(vol_real[:, :, mid_x] - vol_sim[:, :, mid_x], cmap='jet');
    axes[2, 2].set_title('YZ Diff')
    plt.colorbar(im9, ax=axes[2, 2])
    plt.suptitle(f'Tile {exp_name}: Isotropic Analysis (D={D_opt:.5f}, Rho={Rho_opt:.5f})')
    plt.tight_layout()
    plt.savefig(os.path.join(output_plots, 'Ortho_Slices.png'))
    plt.close()

    print(f"[MODEL] Finished. JSONs and Plots saved to {output_plots}")