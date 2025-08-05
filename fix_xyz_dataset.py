try:
    from pathlib import Path
    from tqdm import tqdm
    from icecream import ic
    import hydra
    import numpy as np
    from scipy.signal import find_peaks
    from scipy.stats import gaussian_kde
    from lib.utils_lib import (
        check_dir,
        check_file,
        read_from_xyz_file,
        write_to_xyz_file,
    )
    from lib.electrodes_lib import generate_electrode, adjust_outliers_atoms

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


def check_flake_orientation(X: np.ndarray, Y: np.ndarray) -> bool:
    zero_indices_X = np.where(X <= 0.35)[0]
    zero_indices_Y = np.where(Y <= 0.35)[0]

    common_elements = sum(element in zero_indices_X for element in zero_indices_Y)

    if common_elements == 1:
        return True
    else:
        return False


def mirrors_xyz_structure(X: np.ndarray) -> np.ndarray:
    X = -X
    X -= np.min(X)
    return X


def custom_adjust_outliers_atoms(
    X: np.ndarray,
    Y: np.ndarray,
    cell_x: float = 34.43317005,
    cell_y: float = 34.08,
    delta_x: float = 0.4,
    delta_y: float = 0.4,
):

    new_X = []
    new_Y = []
    for x, y in zip(X, Y):
        if cell_x - x < delta_x:
            x -= cell_x
        if cell_y - y < delta_y:
            y -= cell_y
        new_X.append(x)
        new_Y.append(y)

    return np.array(new_X), np.array(new_Y)


@hydra.main(version_base="1.2", config_path="config", config_name="fix_xyz_dataset")
def main(cfg):
    xyz_files_path = Path(cfg.xyz_files_path)
    out_path = Path(cfg.out_path)
    cell = list(cfg.cell)
    contact_vector = float(cfg.contact_vector)
    nanoribbon_path = Path(cfg.nanoribbon_path)

    check_dir(xyz_files_path)
    check_file(nanoribbon_path)
    out_path.mkdir(exist_ok=True, parents=True)

    files = [f for f in xyz_files_path.iterdir() if f.suffix.lower() == ".xyz"]
    print(files)
    import matplotlib.pyplot as plt
    for file in tqdm(files):
        try:
            atoms, X, Y, Z = read_from_xyz_file(file)

            if len(X) < 5:
                print(f"File {file} ha troppi pochi atomi, salto")
                continue

            kde = gaussian_kde(X)
            x_grid = np.linspace(min(X), max(X), 5000)
            kde_data = kde.evaluate(x_grid)
            
            # Minimum search of KDE
            peaks, _ = find_peaks(-kde_data)
            print(f"Found {peaks} peaks:")

            if len(peaks) == 0:
                print(f"Fallback per {file}: nessun minimo trovato, uso argmin")
                peak_idx = np.argmin(kde_data)
            else:
                peaks = sorted(peaks, key=lambda i: kde_data[i])
                peak_idx = peaks[0]

            cell_x = float(cell[0])
            cell_y = float(cell[4])
            desired_centroid = cell_x / 2
            offset = x_grid[peak_idx] - desired_centroid
        except Exception as e:
        #     print(e)
            continue

        if offset >= 0:
            X[X < offset] += cell_x
        else:
            X[X > (cell_x - abs(offset))] -= cell_x
        X -= np.min(X)
        Y -= np.min(Y)
        X, Y = custom_adjust_outliers_atoms(X, Y, cell_x=cell_x, cell_y=cell_y)
        if not check_flake_orientation(X, Y):
            X = mirrors_xyz_structure(X)
        if not check_flake_orientation(X, Y):
            continue
        write_to_xyz_file(out_path.joinpath(file.name), atoms, X, Y, Z)
        print(out_path.joinpath(file.name))
        generate_electrode(
            file_path=out_path.joinpath(file.name),
            out_path=out_path.joinpath(file.name),
            electrode_path=nanoribbon_path,
            cell=cell,
            contact_vector=contact_vector,
        )
        adjust_outliers_atoms(
            out_path.joinpath(file.name),
            out_path.joinpath(file.name),
            cell_x=cell_x + (2 * contact_vector),
            cell_y=cell_y,
        )


if __name__ == "__main__":
    main()
