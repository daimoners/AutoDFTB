try:
    from pathlib import Path
    import numpy as np
    from tqdm.rich import tqdm

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


def read_from_xyz_file(file_path: Path):
    """Read xyz files and return lists of x,y,z coordinates and atoms"""

    X = []
    Y = []
    Z = []
    atoms = []

    with open(str(file_path), "r") as f:
        num_atom = int(next(f))
        next(f)  # ignore the comment

        for _ in range(num_atom):
            l = next(f).split()
            if len(l) == 4 or len(l) == 5:
                X.append(float(l[1]))
                Y.append(float(l[2]))
                Z.append(float(l[3]))
                atoms.append(str(l[0]))

    X = np.asarray(X)
    Y = np.asarray(Y)
    Z = np.asarray(Z)

    return atoms, X, Y, Z


def cut_device(
    file_path: Path, contact_vector: float, cell_x: float, out_path: Path = None
):

    if out_path is None:
        out_path = file_path.with_stem(f"{file_path.stem}_device")

    atoms, X, Y, Z = read_from_xyz_file(file_path)
    new_coordinates = []

    for atom, x, y, z in zip(atoms, X, Y, Z):
        if x > contact_vector and x < np.max(X) - contact_vector:
            new_coordinates.append((atom, x, y, z))

    with open(str(out_path), "w") as file:
        file.write(f"{len(new_coordinates)}\n")
        file.write("Atoms\n")
        for atom, x, y, z in new_coordinates:
            file.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")


if __name__ == "__main__":
    elecrodes_path = Path(
        "/home/tommaso/git_workspace/AutoDFTB/data/transport/electrodes"
    )
    devices_path = Path("/home/tommaso/git_workspace/AutoDFTB/data/transport/devices")

    electrodes = [f for f in elecrodes_path.iterdir() if f.suffix.lower() == ".xyz"]

    for electrode in tqdm(electrodes):
        cut_device(
            file_path=electrode,
            contact_vector=7.409367073373903,
            cell_x=39.53476932,
            out_path=devices_path.joinpath(electrode.name),
        )
