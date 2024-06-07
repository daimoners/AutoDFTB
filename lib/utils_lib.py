try:
    from pathlib import Path
    import re
    from collections import OrderedDict
    import json
    import os
    import subprocess
    import numpy as np
    from tqdm import tqdm
    from chemfiles import Trajectory
    from PIL import Image, ImageDraw
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


def get_total_electrons(file: Path):
    with open(str(file), "r") as file:
        lines = file.readlines()

        for line in reversed(lines):
            line = line.strip()

            if line:
                match = re.match(r"\d+", line)
                if match:
                    return int(match.group(0))


def get_band_gap(file: Path) -> float:
    """
    Calculates the band gap of a material from its electronic structure data.

    Args:
        file (Path): The path to the file containing the output structure data.

    Returns:
        float: The band gap of the material.

    Raises:
        FileNotFoundError: If the specified file does not exist.

    Example:
        file_path = Path("electronic_structure.dat")
        band_gap = get_band_gap(file_path)
        print(band_gap)
        1.2
    """
    total_electrons = get_total_electrons(file)
    lumo = total_electrons / 2
    homo = lumo + 1

    data = {}
    with open(file, "r") as file:
        lines = file.readlines()

        # Utilizza una espressione regolare per estrarre i numeri dalla riga
        for line, n in zip(reversed(lines), range(total_electrons)):
            match = re.findall(r"\S+", line)
            if len(match) > 1:
                key = int(match[0])
                value = float(match[1])
                data[key] = value

    return data[homo] - data[lumo]


def count_unique_atoms_POSCAR(file_path: Path):
    with open(str(file_path), "r") as file:
        lines = file.readlines()

    # Let's assume that the atomic symbols are listed after the atom count line
    atom_symbols = lines[5].split()

    unique_atoms = set(atom_symbols)
    count = len(unique_atoms)

    return count, unique_atoms


def _map_angular_momentum(file_name: Path) -> str:
    """
    Maps atomic types to their corresponding maximum angular momentum according to the given atom types.

    Args:
        atom_types (list): A list of atomic types.

    Returns:
        str: A string containing the mapped maximum angular momentum for each atom type.

    Example:
        atom_types = ['C', 'O', 'H']
        _map_angular_momentum(atom_types)
        '
            MaxAngularMomentum {
                C = "p"
                O = "p"
                H = "s"
            }
        '
    """
    if file_name.suffix == ".POSCAR":
        poscar_data = get_poscar_data(file_path=file_name)
        atom_types = poscar_data["atom_types"]
    elif file_name.suffix == ".gen":
        atom_types = get_gen_data(file_path=file_name)
    elif file_name.suffix == ".xyz":
        atom_types = get_xyz_types(file_path=file_name)
    else:
        print(f"The {file_name.suffix} extension is not supported")
        raise NotImplementedError

    max_angular_momentum_mapping = {
        "H": "s",
        "He": "s",
        "Li": "s",
        "Be": "s",
        "B": "p",
        "C": "p",
        "N": "p",
        "O": "p",
        "F": "s",
        "Ne": "s",
        "Na": "s",
        "Mg": "s",
        "Al": "p",
        "Si": "p",
        "P": "p",
        "S": "p",
        "Cl": "p",
        "Ar": "s",
        "K": "s",
        "Ca": "s",
        "Sc": "d",
        "Ti": "d",
        "V": "d",
        "Cr": "d",
        "Mn": "d",
        "Fe": "d",
        "Co": "d",
        "Ni": "d",
        "Cu": "d",
        "Zn": "d",
        "Ga": "p",
        "Ge": "p",
        "As": "p",
        "Se": "p",
        "Br": "p",
        "Kr": "s",
        "Rb": "s",
        "Sr": "s",
        "Y": "d",
        "Zr": "d",
        "Nb": "d",
        "Mo": "d",
        "Tc": "d",
        "Ru": "d",
        "Rh": "d",
        "Pd": "d",
        "Ag": "d",
        "Cd": "d",
        "In": "p",
        "Sn": "p",
        "Sb": "p",
        "Te": "p",
        "I": "p",
        "Xe": "s",
        "Cs": "s",
        "Ba": "s",
        "La": "f",
        "Ce": "f",
        "Pr": "f",
        "Nd": "f",
        "Pm": "f",
        "Sm": "f",
        "Eu": "f",
        "Gd": "f",
        "Tb": "f",
        "Dy": "f",
        "Ho": "f",
        "Er": "f",
        "Tm": "f",
        "Yb": "f",
        "Lu": "f",
        "Hf": "d",
        "Ta": "d",
        "W": "d",
        "Re": "d",
        "Os": "d",
        "Ir": "d",
        "Pt": "d",
        "Au": "d",
        "Hg": "d",
        "Tl": "p",
        "Pb": "p",
        "Bi": "p",
        "Po": "p",
        "At": "p",
        "Rn": "s",
        "Fr": "s",
        "Ra": "s",
        "Ac": "f",
        "Th": "f",
        "Pa": "f",
        "U": "f",
        "Np": "f",
        "Pu": "f",
        "Am": "f",
        "Cm": "f",
        "Bk": "f",
        "Cf": "f",
        "Es": "f",
        "Fm": "f",
        "Md": "f",
        "No": "f",
        "Lr": "f",
        "Rf": "d",
        "Db": "d",
        "Sg": "d",
        "Bh": "d",
        "Hs": "d",
        "Mt": "d",
        "Ds": "d",
        "Rg": "d",
        "Cn": "d",
        "Nh": "p",
        "Fl": "p",
        "Mc": "p",
        "Lv": "p",
        "Ts": "p",
        "Og": "p",
    }
    max_angular_momentum = {}
    for atom_type in atom_types:
        max_angular_momentum[atom_type] = max_angular_momentum_mapping.get(
            atom_type, "s"
        )

    def format_max_angular_momentum(max_angular_momentum):
        formatted_output = """
    MaxAngularMomentum {\n"""

        formatted_output += "".join(
            [
                f"\t{atom} = '{momentum}'\n"
                for atom, momentum in max_angular_momentum.items()
            ]
        )
        formatted_output += """
    }"""
        return formatted_output

    formatted_string = format_max_angular_momentum(max_angular_momentum)
    return formatted_string


def get_results(
    values_to_find: list,
    file_path: Path,
    found_values: OrderedDict = None,
    charge: str = None,
) -> OrderedDict:
    """
    Find specified values in a text file.

    Args:
        values_to_find (list): A list of strings representing the values to be found.
        file_path (Path): The path to the text file to search in.
        band_out (Path): The path to the band output file.

    Returns:
        OrderedDict: An ordered dictionary containing the found values where keys are the values found and
        values are the corresponding values extracted from the text file.
    """
    # Dictionary with regex patterns for predefined values
    regex_patterns = {
        "Nr. of electrons (up):": r"\d+",
        "Total Electronic energy:": r"(-?\d+(\.\d+)?)\s+eV",
        "Fermi level:": r"(-?\d+(\.\d+)?)\s+eV",
    }

    if found_values is None:
        found_values = OrderedDict()

    with open(str(file_path), "r") as file:
        for row in file:
            for value in values_to_find:
                if value in row:
                    regex_pattern = regex_patterns.get(value)
                    if regex_pattern:
                        matches = re.findall(regex_pattern, row)
                        if matches:
                            # Extract the value
                            extracted_value = (
                                float(matches[0][0])
                                if len(matches[0]) == 2
                                else float(matches[0])
                            )
                            # Use a mapping to convert the key name to a shorter or more meaningful name
                            if charge is None:
                                key_mapping = {
                                    "Nr. of electrons (up):": "n_electrons",
                                    "Total Electronic energy:": "total_energy_eV",
                                    "Fermi level:": "fermi_level_ev",
                                }
                            elif charge == "+1":
                                key_mapping = {
                                    "Nr. of electrons (up):": "n_electrons_+1",
                                    "Total Electronic energy:": "total_energy_eV_+1",
                                    "Fermi level:": "fermi_level_ev_+1",
                                }
                            elif charge == "-1":
                                key_mapping = {
                                    "Nr. of electrons (up):": "n_electrons_-1",
                                    "Total Electronic energy:": "total_energy_eV_-1",
                                    "Fermi level:": "fermi_level_ev_-1",
                                }
                            short_key = key_mapping.get(value, value)
                            found_values[short_key] = extracted_value
                        else:
                            found_values[value] = None

    return found_values


def get_poscar_data(file_path: Path):
    """
    Reads a VASP POSCAR file and extracts relevant information.

    Args:
        file_path (Path): The path to the POSCAR file.

    Returns:
        dict: A dictionary containing the extracted data including scale factor, cell box dimensions,
            atom types, number of atoms per type, and atomic coordinates.

    Example:
        file_path = Path("POSCAR")
        data = get_poscar_data(file_path)
        print(data)
        {
            'scale_factor': 1.0,
            'cell_box': [[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
            'atom_types': ['C', 'H'],
            'num_atoms': [4, 8],
            'coordinates': [[0.0, 0.0, 0.0], [0.5, 0.5, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5],
                            [0.25, 0.25, 0.25], [0.75, 0.75, 0.25], [0.25, 0.75, 0.75], [0.75, 0.25, 0.75]]
        }
    """
    with open(str(file_path), "r") as f:
        lines = f.readlines()

    scale_factor = float(lines[1])
    cell_box = [[float(x) for x in linea.split()] for linea in lines[2:5]]
    atom_types = lines[5].split()
    num_atoms = [int(x) for x in lines[6].split()]

    coordinates = []
    for line in lines[8:]:
        coordinates.append([float(x) for x in line.split()])

    poscar_data = {
        "scale_factor": scale_factor,
        "cell_box": cell_box,
        "atom_types": atom_types,
        "num_atoms": num_atoms,
        "coordinates": coordinates,
    }

    return poscar_data


def get_xyz_types(file_path: Path) -> list[str]:
    atom_types = []

    with open(file_path, "r") as f:
        lines = f.readlines()

    num_atoms = int(lines[0])

    for line in lines[2 : 2 + num_atoms]:
        atom_symbol = line.split()[0]
        if atom_symbol not in atom_types:
            atom_types.append(atom_symbol)
    return atom_types


def get_gen_data(file_path: Path) -> list[str]:
    with open(file_path, "r") as f:
        lines = f.readlines()

    atom_types = lines[1]
    atom_list = re.findall(r"\b\w\b", atom_types)
    print(atom_list)
    return atom_list


def xyz2gen(
    xyz_path: Path,
    out_path: Path = None,
    cell: list = [100.0, 100.0, 100.0],
    supercell: bool = True,
):
    if not xyz_path.is_file() or not xyz_path.suffix.lower() == ".xyz":
        raise Exception(f"File {str(xyz_path)} not found!")

    if not out_path:
        out_path = xyz_path.with_suffix(".gen")

    aa = cell[0]
    bb = cell[1]
    cc = cell[2]

    with open(str(xyz_path), "r") as FPin:
        natm = int(FPin.readline().strip())
        FPin.readline()  # skip the second line

        atm = []
        isp = {}
        x = []
        y = []
        z = []

        for i in range(natm):
            line = FPin.readline().split()
            atm_symbol = line[0]
            atm.append(atm_symbol)
            x_coord, y_coord, z_coord = map(float, line[1:])
            x.append(x_coord)
            y.append(y_coord)
            z.append(z_coord)
            if atm_symbol not in isp:
                isp[atm_symbol] = len(isp) + 1

    with open(str(out_path), "w") as output:
        if supercell:
            output.write(f" {natm} {'S'}\n")
        else:
            output.write(f" {natm} {'C'}\n")

        unique_atoms = set(atm)
        output.write(" ")
        for atom in unique_atoms:
            output.write(f" {atom}")
        output.write("\n")

        for i in range(natm):
            output.write(
                f"{i + 1} {isp[atm[i]]} {x[i]:18.12f} {y[i]:18.12f} {z[i]:18.12f}\n"
            )

        if supercell:
            output.write("0.000000000000 0.0000000000000 0.0000000000000\n")
            output.write(f"{aa:18.12f} 0.000000000000 0.0000000000000\n")
            output.write(f"0.000000000000 {bb:18.12f} 0.0000000000000\n")
            output.write(f"0.000000000000 0.0000000000000 {cc:18.12f}\n")


def get_cell_from_gen(
    file_path: Path, json_output_path: Path = None, custom_name: str = None
):

    if file_path.suffix.lower() != ".gen":
        raise Exception(f"Wrong file format for {file_path}!")

    with open(str(file_path), "r") as f:
        lines = f.readlines()

    match = re.match(
        r"^\s{4}(\d\.\d{10}E\+\d{2})\s{4}(\d\.\d{10}E\+\d{2})\s{4}(\d\.\d{10}E\+\d{2})$",
        lines[-3],
    )
    if match:
        a = float(match.group(1))

    match = re.match(
        r"^\s{4}(\d\.\d{10}E\+\d{2})\s{4}(\d\.\d{10}E\+\d{2})\s{4}(\d\.\d{10}E\+\d{2})$",
        lines[-2],
    )
    if match:
        b = float(match.group(2))

    match = re.match(
        r"^\s{4}(\d\.\d{10}E\+\d{2})\s{4}(\d\.\d{10}E\+\d{2})\s{4}(\d\.\d{10}E\+\d{2})$",
        lines[-1],
    )
    if match:
        c = float(match.group(3))

    if json_output_path is not None:
        dict = {
            "file_name": file_path.stem if custom_name is None else custom_name,
            "cell": [a, 0.0, 0.0, 0.0, b, 0.0, 0.0, 0.0, c],
        }
        with open(str(json_output_path), "w") as f:
            json.dump(dict, f, indent=4)

    return [a, 0.0, 0.0, 0.0, b, 0.0, 0.0, 0.0, c]


def launch_bin(
    bin_path: Path,
    working_dir: Path,
    verbose: bool = True,
    write_out_file: Path = None,
):
    os.chdir(str(working_dir))
    if write_out_file is None:
        process = subprocess.Popen(
            [str(bin_path)],
            shell=True,
            stdout=subprocess.PIPE if not verbose else None,
            stderr=subprocess.PIPE if not verbose else None,
        )
        process.wait()
    else:
        with open(str(write_out_file), "w") as output_file:
            process = subprocess.Popen(
                [str(bin_path)],
                shell=True,
                stdout=output_file,
                stderr=subprocess.PIPE if not verbose else None,
            )
            process.wait()
    os.chdir(str(Path().resolve()))


def check_dir(dir_path: Path | list[Path]):
    if isinstance(dir_path, list):
        for dir in dir_path:
            if not dir.is_dir():
                raise Exception(f"{dir} it's not a directory or it doesn't exist")
    elif isinstance(dir_path, Path):
        if not dir_path.is_dir():
            raise Exception(f"{dir_path} it's not a directory or it doesn't exist")


def check_file(file_path: Path | list[Path]):
    if isinstance(file_path, list):
        for file in file_path:
            if not file.is_file():
                raise Exception(f"{file} it's not a file or it doesn't exist")
    elif isinstance(file_path, Path):
        if not file_path.is_file():
            raise Exception(f"{file_path} it's not a file or it doesn't exist")


def translate_xyz_file(
    file_path: Path,
    out_path: Path = None,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    z_offset: float = 0.0,
):
    if file_path.suffix.lower() != ".xyz":
        raise Exception(f"Wrong suffix for file {file_path.name}!")
    if out_path is None:
        out_path = file_path

    atoms, X, Y, Z = read_from_xyz_file(file_path)

    new_coordinates = []
    for atom, x, y, z in zip(atoms, X, Y, Z):  # device
        x += x_offset
        y += y_offset
        z += z_offset
        new_coordinates.append((atom, x, y, z))

    with open(str(out_path), "w") as file:
        file.write(f"{len(new_coordinates)}\n")
        file.write("Atoms\n")
        for atom, x, y, z in new_coordinates:
            file.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")


def move_xyz_to_origin(file_path: Path, out_path: Path = None):
    if file_path.suffix.lower() != ".xyz":
        raise Exception(f"Wrong suffix for file {file_path.name}!")
    if out_path is None:
        out_path = file_path

    new_coordinates = []

    atoms, X, Y, Z = read_from_xyz_file(file_path)
    offset_x = np.min(X)
    offset_y = np.min(Y)
    for atom, x, y, z in zip(atoms, X, Y, Z):  # device
        x += -offset_x
        y += -offset_y
        new_coordinates.append((atom, x, y, z))

    with open(str(out_path), "w") as file:
        file.write(f"{len(new_coordinates)}\n")
        file.write("Atoms\n")
        for atom, x, y, z in new_coordinates:
            file.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")


def get_current_value(file_path: Path, json_file: Path = None):
    with open(str(file_path), "r") as f:
        lines = f.readlines()

    for line in lines:
        match = re.findall(
            r"current\:\s+(\d\.\d+E\S\d*)\sA",
            line,
        )
        if len(match) == 1:
            current = float(match[0])
            break

    return current


def write_to_xyz_file(file_path: Path, atoms, X, Y, Z):
    """Write data to an xyz file"""

    with open(str(file_path), "w") as f:
        f.write(f"{len(atoms)}\n")
        f.write(
            "Generated by write_to_xyz_file\n"
        )  # Si può modificare questo commento a piacere

        for atom, x, y, z in zip(atoms, X, Y, Z):
            f.write(f"{atom} {x:.6f} {y:.6f} {z:.6f}\n")


class Utils:
    IMAGE_EXTENSIONS = (".jpg", ".png", ".jpeg")

    @staticmethod
    def generate_bonds_png(
        spath: Path,
        dpath: Path,
        max_dim: list,
        multiplier: int = 3,
    ):

        with Trajectory(str(spath)) as trajectory:
            mol = trajectory.read()

        resolution = round(
            multiplier * (5 + np.max([np.abs(max_dim[0]), np.abs(max_dim[1])]))
        )

        B = Image.new("RGB", (resolution, resolution))
        B_ = ImageDraw.Draw(B)

        mol.guess_bonds()
        if mol.topology.bonds_count() == 0:
            print(f"No bonds guessed for {spath.stem}\n")
        bonds = mol.topology.bonds

        for i in range(len(bonds)):
            x_1 = int(round(mol.positions[bonds[i][0]][0] * multiplier))
            y_1 = int(round(mol.positions[bonds[i][0]][1] * multiplier))
            x_2 = int(round(mol.positions[bonds[i][1]][0] * multiplier))
            y_2 = int(round(mol.positions[bonds[i][1]][1] * multiplier))
            line = [(x_1, y_1), (x_2, y_2)]
            first_atom = mol.atoms[bonds[i][0]].name
            second_atom = mol.atoms[bonds[i][1]].name
            color = Utils.find_bound_type(first_atom, second_atom)
            B_.line(line, fill=color, width=0)

        B = Utils.crop_image(B)
        B.save(str(dpath.joinpath(f"{spath.stem}.png")))

    @staticmethod
    def find_bound_type(first_atom: str, second_atom: str) -> str:
        if (first_atom == "C" and second_atom == "C") or (
            second_atom == "C" and first_atom == "C"
        ):
            return "red"
        elif (first_atom == "C" and second_atom == "O") or (
            second_atom == "O" and first_atom == "C"
        ):
            return "blue"
        elif (first_atom == "O" and second_atom == "H") or (
            second_atom == "H" and first_atom == "O"
        ):
            return "white"
        elif (first_atom == "C" and second_atom == "H") or (
            second_atom == "H" and first_atom == "C"
        ):
            return "yellow"

    @staticmethod
    def crop_image(image: Image, name: str = None, dpath: Path = None) -> Image:

        image_data = np.asarray(image)
        if len(image_data.shape) == 2:
            image_data_bw = image_data
        else:
            image_data_bw = image_data.max(axis=2)
        non_empty_columns = np.where(image_data_bw.max(axis=0) > 0)[0]
        non_empty_rows = np.where(image_data_bw.max(axis=1) > 0)[0]
        cropBox = (
            min(non_empty_rows),
            max(non_empty_rows),
            min(non_empty_columns),
            max(non_empty_columns),
        )

        if len(image_data.shape) == 2:
            image_data_new = image_data[
                cropBox[0] : cropBox[1] + 1, cropBox[2] : cropBox[3] + 1
            ]
        else:
            image_data_new = image_data[
                cropBox[0] : cropBox[1] + 1, cropBox[2] : cropBox[3] + 1, :
            ]

        new_image = Image.fromarray(image_data_new)
        if dpath is not None:
            new_image.save(dpath.joinpath(name))

        return new_image

    @staticmethod
    def from_xyz_to_png(
        spath: Path,
        dpath: Path,
        max_dim: list,
        items: int = None,
        multiplier: int = 6,
    ):
        if dpath.is_dir():
            print(f"WARNING: the directory {dpath} already exists!")
            return
        else:
            dpath.mkdir(exist_ok=True, parents=True)

        files = [f for f in spath.iterdir() if f.suffix.lower() == ".xyz"]
        if items is None:
            items = len(files)

        pbar = tqdm(total=len(files) if items > len(files) else items)
        for i, file in enumerate(files):
            if i >= items:
                break
            Utils.generate_bonds_png(file, dpath, max_dim, multiplier)
            pbar.update(1)
        pbar.close()

    @staticmethod
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

    @staticmethod
    def check_x_interface_num_atoms(
        file_path: Path,
        num_atoms: int = 32,
        delta: float = 1.42,
    ):
        atoms, X, Y, Z = Utils.read_from_xyz_file(file_path)

        y_up = [y for y in Y if max(Y) - delta <= y <= max(Y)]
        y_down = [y for y in Y if min(Y) <= y <= min(Y) + delta]

        if len(y_up) == len(y_down) == num_atoms:
            return True
        else:
            ic(
                f"Warning, {file_path.name} failed check interface atom counts ({len(y_up)}!={len(y_down)}!={num_atoms}) and will be deleted!"
            )
            return False


if __name__ == "__main__":
    # slakos = Path('/home/mario/app/dftbplus/slakos/pbc-0-3')
    # in_file = Path('/home/mario/AutoDFTB/graphene_68.POSCAR')
    # prepare_dftbplus_input(in_file, slakos=slakos)
    pass
