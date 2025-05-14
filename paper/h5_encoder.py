try:
    import h5py
    import pandas as pd
    from PIL import Image
    import numpy as np
    from pathlib import Path
    from tqdm.rich import tqdm

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


def compute_inertia_tensor(xyz_file: Path):
    # Atomic masses for common elements (in atomic mass units)
    atomic_masses = {
        "H": 1.00784,
        "C": 12.011,
        "O": 15.999,
    }

    def read_xyz_file(filename):
        """Read atomic symbols and coordinates from an XYZ file."""
        with open(filename, "r") as f:
            lines = f.readlines()

        N = int(lines[0].strip())  # Number of atoms
        comment_line = lines[1].strip()  # Optional comment line (ignored here)

        atoms = []
        coordinates = []

        for line in lines[2 : 2 + N]:
            parts = line.split()
            atom = parts[0]
            x, y, z = map(float, parts[1:])
            atoms.append(atom)
            coordinates.append([x, y, z])

        return atoms, np.array(coordinates)

    def compute_center_of_mass(atoms, coordinates):
        """Calculate the center of mass of the molecule."""
        total_mass = sum(atomic_masses[atom] for atom in atoms)
        R_cm = sum(
            atomic_masses[atoms[i]] * coordinates[i] for i in range(len(atoms))
        ) / total_mass
        return R_cm

    def compute_inertia_tensor_matrix(atoms, coordinates):
        """Compute the inertia tensor with respect to the center of mass."""
        translated_coords = coordinates - compute_center_of_mass(atoms, coordinates)

        I = np.zeros((3, 3))

        for i, atom in enumerate(atoms):
            m = atomic_masses[atom]
            x, y, z = translated_coords[i]

            # Diagonal elements
            I[0, 0] += m * (y**2 + z**2)
            I[1, 1] += m * (x**2 + z**2)
            I[2, 2] += m * (x**2 + y**2)

            # Off-diagonal elements (negative terms)
            I[0, 1] -= m * x * y
            I[0, 2] -= m * x * z
            I[1, 2] -= m * y * z

        # Fill symmetric entries
        I[1, 0] = I[0, 1]
        I[2, 0] = I[0, 2]
        I[2, 1] = I[1, 2]

        return I

    # Read atomic structure from the XYZ file
    atoms, coordinates = read_xyz_file(str(xyz_file))

    # Compute the inertia tensor
    inertia_tensor = compute_inertia_tensor_matrix(atoms, coordinates)

    return inertia_tensor


def read_from_xyz_file(file_path: Path):
    """Read xyz files and return lists of x,y,z coordinates and atoms"""

    symbol_to_atomic_number = {
        "H": 1,
        "He": 2,
        "Li": 3,
        "Be": 4,
        "B": 5,
        "C": 6,
        "N": 7,
        "O": 8,
        "F": 9,
        "Ne": 10,
        "Na": 11,
        "Mg": 12,
        "Al": 13,
        "Si": 14,
        "P": 15,
        "S": 16,
        "Cl": 17,
        "Ar": 18,
        "K": 19,
        "Ca": 20,
        # Aggiungi altri elementi se necessario
    }

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

                atomic_number = symbol_to_atomic_number.get(str(l[0]))
                if atomic_number is None:
                    raise ValueError(f"Simbolo chimico sconosciuto: {str(l[0])}")
                atoms.append(atomic_number)

    X = np.asarray(X)
    Y = np.asarray(Y)
    Z = np.asarray(Z)

    coords = np.stack((X, Y, Z), axis=1)

    return atoms, coords


def main(package_path, output_path, csv_file, samples_for_file):

    # Leggi il file CSV
    df = pd.read_csv(csv_file)

    # Calcola il numero totale di slice necessari
    num_slices = len(df) // samples_for_file + (len(df) % samples_for_file != 0)

    # Divide il DataFrame in slice
    slices = [
        df[i * samples_for_file : (i + 1) * samples_for_file] for i in range(num_slices)
    ]

    # Crea un file HDF5
    for i, slice_df in enumerate(slices):
        with h5py.File(output_path.joinpath(f"dataset_{i}.h5"), "w") as h5f:
            # Attributi generali
            h5f.attrs["title"] = "Dataset Esempio FAIR"
            h5f.attrs["description"] = (
                "Un esempio di come creare un dataset HDF5 seguendo i principi FAIR."
            )
            h5f.attrs["author"] = "Nome Ricercatore"
            h5f.attrs["created"] = "2024-07-23"
            h5f.attrs["license"] = "CC-BY-4.0"
            h5f.attrs["doi"] = "10.1234/example.doi"
            h5f.attrs["url"] = "https://zenodo.org/record/1234567"
            h5f.attrs["version"] = "1.0"
            h5f.attrs["last_updated"] = "2024-07-23"

            # Documentazione
            docs_group = h5f.create_group("documentation")
            docs_group.attrs["description"] = (
                "Documentazione completa sul dataset e sulle metodologie utilizzate."
            )
            docs_group.create_dataset(
                "full_description",
                data=np.string_("Questo dataset contiene..."),
            )

            pbar = tqdm(total=len(slice_df))
            for index, row in slice_df.iterrows():
                file_name = row[0]
                json_data = row[1:].to_dict()
                image_path = package_path.joinpath(
                    f"data_batch_{json_data['batch']}",
                    "transport",
                    "stm_images",
                    f"{file_name}_e.png",
                )

                # Carica l'immagine e convertila in un array numpy
                image = Image.open(image_path)
                image_array = np.array(image)

                master_group = h5f.create_group(f"{file_name}")
                master_group.attrs["description"] = (
                    f"Simulated data regarding the flake: {file_name}"
                )

                # STM image
                stm_data = master_group.create_dataset(
                    "STM_image",
                    data=image_array,
                    compression="gzip",
                    compression_opts=9,
                )
                stm_data.attrs["description"] = "STM image of the flake"

                # Optimized geometry
                atoms, coords = read_from_xyz_file(
                    package_path.joinpath(
                        f"data_batch_{json_data['batch']}",
                        "dftb",
                        "xyz_files_fixed_opt",
                        f"{file_name}_opt.xyz",
                    )
                )
                optimized_geom = master_group.create_group("OptGeom")

                atoms_data = optimized_geom.create_dataset("AtomicNumbers", data=atoms)
                atoms_data.attrs["description"] = ""

                coords_data = optimized_geom.create_dataset("Coordinates", data=coords)
                coords_data.attrs["units"] = "Ang"
                coords_data.attrs["description"] = ""

                inertia_data = optimized_geom.create_dataset(
                    "InertiaTensor",
                    data=compute_inertia_tensor(
                        package_path.joinpath(
                            f"data_batch_{json_data['batch']}",
                            "dftb",
                            "xyz_files_fixed_opt",
                            f"{file_name}_opt.xyz",
                        )
                    ),
                )
                inertia_data.attrs["units"] = "amu*Ang^2"
                inertia_data.attrs["description"] = ""

                # Num atoms
                n_atoms_data = master_group.create_dataset(
                    "NumAtoms", data=np.array(json_data["num_atoms"])
                )
                n_atoms_data.attrs["description"] = "Number of atoms of the flake"

                # Num electrons
                n_electrons_data = master_group.create_dataset(
                    "NumElectrons", data=np.array(json_data["num_electrons"])
                )
                n_electrons_data.attrs["description"] = (
                    "Number of electrons of the flake"
                )

                # Total energy
                total_energy_data = master_group.create_dataset(
                    "TotalEnergy", data=np.array(json_data["total_energy"])
                )
                total_energy_data.attrs["units"] = "eV"
                total_energy_data.attrs["description"] = "Total energy of the flake"

                # Fermi_energy
                fermi_energy_data = master_group.create_dataset(
                    "FermiEnergy", data=np.array(json_data["Fermi_energy"])
                )
                fermi_energy_data.attrs["units"] = "eV"
                fermi_energy_data.attrs["description"] = "Fermi energy of the flake"

                # EA
                EA_data = master_group.create_dataset(
                    "EA", data=np.array(json_data["electron_affinity"])
                )
                EA_data.attrs["units"] = "eV"
                EA_data.attrs["description"] = "Electron affinity of the flake"

                # IP
                IP_data = master_group.create_dataset(
                    "IP", data=np.array(json_data["ionization_potential"])
                )
                IP_data.attrs["units"] = "eV"
                IP_data.attrs["description"] = "Ionization potential of the flake"

                # Band gap
                band_gap_data = master_group.create_dataset(
                    "BandGap", data=np.array(json_data["band_gap"])
                )
                band_gap_data.attrs["units"] = "eV"
                band_gap_data.attrs["description"] = "Band gap of the flake"

                # Optimized electrodes
                atoms, coords = read_from_xyz_file(
                    package_path.joinpath(
                        f"data_batch_{json_data['batch']}",
                        "transport",
                        "electrodes",
                        f"{file_name}_e.xyz",
                    )
                )
                electrodes = master_group.create_group("Electode")

                e_atoms_data = electrodes.create_dataset("AtomicNumbers", data=atoms)
                e_atoms_data.attrs["description"] = ""

                e_coords_data = electrodes.create_dataset("Coordinates", data=coords)
                e_coords_data.attrs["units"] = "Armstrong"
                e_coords_data.attrs["description"] = ""

                e_inertia_data = electrodes.create_dataset(
                    "InertiaTensor",
                    data=compute_inertia_tensor(
                        package_path.joinpath(
                            f"data_batch_{json_data['batch']}",
                            "transport",
                            "electrodes",
                            f"{file_name}_e.xyz",
                        )
                    ),
                )
                e_inertia_data.attrs["units"] = "amu*Ang^2"
                e_inertia_data.attrs["description"] = ""

                # Current
                current_data = master_group.create_dataset(
                    "TransportCurrent", data=np.array(json_data["current"])
                )
                current_data.attrs["units"] = "uA"
                current_data.attrs["description"] = "Transport current of the flake"

                pbar.update(1)

            pbar.close()


if __name__ == "__main__":
    package_path = Path("/home/tommaso/git_workspace/AutoDFTB")
    output_path = Path("./h5_files")
    csv_file = Path("./dataset.csv")
    samples_for_file = 10000
    main(package_path, output_path, csv_file, samples_for_file)
