try:
    from pathlib import Path
    from ase.structure import graphene_nanoribbon
    import numpy as np
    import math
    from icecream import ic

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


def adjust_outliers_atoms(
    file_path: Path,
    out_path: Path,
    cell_x: float = 34.43317005,
    cell_y: float = 34.08,
    delta_x: float = 0.4,
    delta_y: float = 0.4,
):

    atoms, X, Y, Z = read_from_xyz_file(file_path)
    new_coordinates = []
    for atom, x, y, z in zip(atoms, X, Y, Z):
        if cell_x - x < delta_x:
            x -= cell_x
        if cell_y - y < delta_y:
            y -= cell_y
        new_coordinates.append((atom, x, y, z))

    with open(str(out_path), "w") as f:
        f.write(f"{len(new_coordinates)}\n")
        f.write("Atoms\n")
        for atom, x, y, z in new_coordinates:
            f.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")


def check_interface_num_atoms(
    file_path: Path,
    cell_y: float = 34.08,
    delta: float = 1.88,
    bond_lenght: float = 1.42,
):
    num_atoms = int(cell_y / (3 / 2 * bond_lenght)) * 2
    atoms, X, Y, Z = read_from_xyz_file(file_path)

    x_left = [x for x in X if min(X) <= x <= min(X) + delta]
    x_right = [x for x in X if max(X) - delta <= x <= max(X)]

    if len(x_left) == len(x_right) == num_atoms:
        return True
    else:
        ic(
            f"Warning, {file_path.name} failed check interface atom counts and will be deleted!"
        )
        return False


def get_electrode(
    out_path: Path, x_len: int = 3, y_len: int = 8, type: str = "armchair"
):
    # Genera un foglio di grafene ideale
    graphene_sheet = graphene_nanoribbon(x_len, y_len, type, sheet=True)
    # Salva la struttura in un file XYZ
    graphene_sheet.write(out_path)

    def rotate_structure(input_file, output_file, rotation_matrix):
        with open(input_file, "r") as f_in:
            lines = f_in.readlines()

        # Get the number of atoms and the cell parameters from the input file
        num_atoms = int(lines[0])

        # Extract atomic positions
        atoms = []
        for line in lines[2 : 2 + num_atoms]:
            atoms.append(list(map(float, line.split()[1:])))

        # Convert atomic positions to numpy array for matrix multiplication
        atoms = np.array(atoms)

        # Apply rotation to atomic positions
        rotated_atoms = np.dot(atoms, rotation_matrix)

        # Write the rotated structure to the output file
        with open(output_file, "w") as f_out:
            f_out.write(f"{num_atoms}\n")
            f_out.write(lines[1])  # Copy comment line from the input file
            for i in range(num_atoms):
                atom_line = (
                    " ".join(
                        map(str, [lines[i + 2].split()[0]] + list(rotated_atoms[i]))
                    )
                    + "\n"
                )
                f_out.write(atom_line)

    # Usage example
    rotation_matrix = np.array(
        [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    )  # Example rotation matrix (90 degree rotation around y-axis)
    rotate_structure(out_path, out_path, rotation_matrix)


def generate_electrode(
    file_path: Path,
    out_path: Path,
    electrode_path: Path,
    cell_x: float = 34.43317005,
    bond_lenght: float = 1.42,
):

    atoms_el, X_el, Y_el, Z_el = read_from_xyz_file(electrode_path)

    offset = max(X_el) + bond_lenght * math.cos(math.pi / 6)

    new_coordinates = []
    for atom, x, y, z in zip(atoms_el, X_el, Y_el, Z_el):
        new_coordinates.append((atom, x, y, z))

    atoms, X, Y, Z = read_from_xyz_file(file_path)
    for atom, x, y, z in zip(atoms, X, Y, Z):
        x += offset
        new_coordinates.append((atom, x, y, z))

    for atom, x, y, z in zip(atoms_el, X_el, Y_el, Z_el):
        x += offset + cell_x
        new_coordinates.append((atom, x, y, z))

    with open(str(out_path), "w") as file:
        file.write(f"{len(new_coordinates)}\n")
        file.write("Atoms\n")
        for atom, x, y, z in new_coordinates:
            file.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")


if __name__ == "__main__":
    pass
