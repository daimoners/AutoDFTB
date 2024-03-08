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


def get_band_gap(file: Path):
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


def prepare_dftbplus_input(
    file_name: Path,
    slakos: Path,
    iterations: int = 200,
    fermi_temperature: float = 1000.0,
    charge: int = None,
):
    geometry = (
        """Geometry = VaspFormat {
    <<< """
        + f"'{file_name.name}'"
        + """
}

Driver {}
    """
    )
    hamiltonian = (
        """\nHamiltonian = DFTB {
    Scc = Yes
    SlaterKosterFiles = Type2FileNames {
    Prefix = """
        + f"'{slakos}/'"
        + """
    Separator = "-"
    Suffix = ".skf"
    }
    MaxAngularMomentum {
    C = "p"
    }
    MaxSCCIterations = """
        + f"{iterations}"
        + """
    Filling = Fermi {
        Temperature [K] = """
        + f"{fermi_temperature}"
        + """
    }
    KPointsAndWeights = SupercellFolding {
    1 0 0
    0 1 0
    0 0 1
    0.5 0.5 0.0
    }
    """
        + (f"Charge = {charge}" if charge is not None else " ")
        + """
}"""
    )
    other_options = """\n\nOptions {
    WriteDetailedXml = Yes
}

Analysis {
    CalculateForces = Yes
    WriteEigenvectors = Yes
}

ParserOptions {
    ParserVersion = 12
}"""
    with open(str(file_name.with_name("dftb_in.hsd")), "w") as f:
        f.write(geometry + hamiltonian + other_options)


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
    pass
