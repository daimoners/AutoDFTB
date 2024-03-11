try:
    from pathlib import Path
    import re
    from collections import OrderedDict

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


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
    poscar_data = get_poscar_data(file_path=file_name)
    atom_types = poscar_data["atom_types"]
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


if __name__ == "__main__":
    # slakos = Path('/home/mario/app/dftbplus/slakos/pbc-0-3')
    # in_file = Path('/home/mario/AutoDFTB/graphene_68.POSCAR')
    # prepare_dftbplus_input(in_file, slakos=slakos)
    pass
