from lib.dftb_lib import prepare_dftbplus_input
from dataclasses import dataclass
from pathlib import Path
from lib.poscar_lib import xyz_to_poscar
from lib.electrodes_lib import get_electrode, read_from_xyz_file
import numpy as np
import math
import json


@dataclass
class input_dftb:
    optimize_geometry: bool
    max_steps: int
    slakos: str
    fermi_temperature: float
    max_iterations: int
    charge: int


def main(file: Path):
    args = input_dftb(
        optimize_geometry=False,
        max_steps=0,
        slakos="/home/tommaso/Applications/dftbplus/slakos/pbc-0-3/",
        fermi_temperature=1000.0,
        max_iterations=200,
        charge=0,
    )

    prepare_dftbplus_input(args, file)


def flessibile(xyz_file: Path):
    atoms, X, Y, Z = read_from_xyz_file(xyz_file)

    destro = []
    sinistro = []

    for atom, x, y, z in zip(atoms, X, Y, Z):
        if x >= np.mean(X):
            destro.append((atom, x, y, z))
        else:
            sinistro.append((atom, x, y, z))

    with open(str(xyz_file.with_name(f"{xyz_file.stem}_dx.xyz")), "w") as f:
        f.write(f"{len(destro)}\n")
        f.write("Atoms\n")
        for atom, x, y, z in destro:
            f.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")

    with open(str(xyz_file.with_name(f"{xyz_file.stem}_sx.xyz")), "w") as f:
        f.write(f"{len(sinistro)}\n")
        f.write("Atoms\n")
        for atom, x, y, z in sinistro:
            f.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")


def generate_electrode(
    file_path: Path,
    out_path: Path,
    electrode_path: Path,
    cell_x: float = 34.43317005,
    bond_lenght: float = 1.42,
):

    atoms_el, X_el, Y_el, Z_el = read_from_xyz_file(electrode_path)

    offset = max(X_el) + bond_lenght * math.cos(math.pi / 6)

    atom_range = {}
    new_coordinates = []

    atoms, X, Y, Z = read_from_xyz_file(file_path)
    for atom, x, y, z in zip(atoms, X, Y, Z):  # device
        x += offset
        new_coordinates.append((atom, x, y, z))

    atom_range["device"] = [1, len(atoms)]
    atom_range["source"] = [
        atom_range["device"][1] + 1,
        atom_range["device"][1] + 2 * len(atoms_el),
    ]
    atom_range["drain"] = [
        atom_range["source"][1] + 1,
        atom_range["source"][1] + 2 * len(atoms_el),
    ]

    for atom, x, y, z in zip(atoms_el, X_el, Y_el, Z_el):  # source
        new_coordinates.append((atom, x, y, z))
    for atom, x, y, z in zip(atoms_el, X_el, Y_el, Z_el):  # source
        x += max(X_el) + bond_lenght
        new_coordinates.append((atom, x, y, z))

    for atom, x, y, z in zip(atoms_el, X_el, Y_el, Z_el):  # drain
        x += offset + cell_x
        new_coordinates.append((atom, x, y, z))
    for atom, x, y, z in zip(atoms_el, X_el, Y_el, Z_el):  # drain
        x += offset + cell_x + max(X_el) + bond_lenght
        new_coordinates.append((atom, x, y, z))

    with open(str(out_path), "w") as file:
        file.write(f"{len(new_coordinates)}\n")
        file.write("Atoms\n")
        for atom, x, y, z in new_coordinates:
            file.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")

    with open(str(out_path.with_suffix(".json")), "w") as f:
        json.dump(atom_range, f, indent=4)


if __name__ == "__main__":
    # get_electrode(
    #     Path("/home/tommaso/git_workspace/AutoDFTB/tmp/electrode.xyz"),
    #     x_len=2,
    #     y_len=8,
    #     sheet=False,
    # )
    # flessibile(Path("/home/tommaso/git_workspace/AutoDFTB/tmp/electrode.xyz"))
    # xyz_path = Path("/home/tommaso/git_workspace/AutoDFTB/tmp/graphene_416_fixed_e.xyz")
    # xyz_to_poscar(
    #     xyz_path,
    #     poscar_file=xyz_path.with_suffix(".POSCAR"),
    #     default_box_size=[34.43317005, 0.0, 0.0, 0.0, 34.08, 0.0, 0.0, 0.0, 10.0],
    # )
    # main(xyz_path.with_suffix(".POSCAR"))
    generate_electrode(
        Path("/home/tommaso/git_workspace/AutoDFTB/tmp/graphene_416_fixed.xyz"),
        Path("/home/tommaso/git_workspace/AutoDFTB/tmp/graphene_416_fixed_e.xyz"),
        Path("/home/tommaso/git_workspace/AutoDFTB/tmp/electrode_sx.xyz"),
    )
