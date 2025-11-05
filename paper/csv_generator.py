import pandas as pd
import json
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from tqdm import tqdm

# setup logging
logging.basicConfig(level=logging.INFO, format="%(processName)s - %(message)s")
def get_num_atoms(file_xyz):
    try:
        with open(file_xyz, 'r') as file:
            first_line = file.readline()
            n_atoms = int(first_line.strip())
            return n_atoms
    except Exception as e:
        print(f"Error: {e}")
        return None
def process_file(file, dataset, xyz_files_path, batch):
    try:
        logging.info(f"Processing {file.name} in batch {batch}")
        with open(file, "r") as f:
            data = json.load(f)
        transport_file = dataset / "transport" / "transport_output" / f"{data['file_name'][:-4]}_e.json"
        with open(transport_file, "r") as f:
            data_current = json.load(f)
        return {
            "file_name": data["file_name"][:-4],
            "num_electrons": data["n_electrons"],
            "Fermi_energy": data["fermi_level_ev"],
            "total_energy": data["total_electronic_energy_eV"],
            "electron_affinity": data["total_energy_eV"] -data["total_energy_eV_+1"],
            "ionization_potential": data["total_energy_eV_-1"] - data["total_energy_eV"] ,
            "band_gap": data["total_energy_eV_-1"] - 2*data["total_energy_eV"] + data["total_energy_eV_+1"],
            "total_energy+1": data["total_energy_eV_+1"],
            "total_energy-1": data["total_energy_eV_-1"],
            "current": data_current["current"],
            "batch": batch,
            "num_atoms": get_num_atoms(xyz_files_path / f"{data['file_name'][:-4]}.xyz")

        }
    except FileNotFoundError:
        return None


root = Path.cwd().parent
batches = [2,3,4,5,6,7,8,9,10,11,12,13]
results = []

for batch in batches:
    dataset = root / f"data_batch_{batch}"
    xyz_files_path = dataset / "xyz_files_fixed"
    dftb_files = list((dataset / "dftb" / "new_json_files").glob("*.json"))

    logging.info(f"Starting batch {batch} with {len(dftb_files)} files")

    worker = partial(process_file, dataset=dataset, xyz_files_path=xyz_files_path, batch=batch)

    with ProcessPoolExecutor() as ex:
        batch_results = list(
            tqdm(ex.map(worker, dftb_files), total=len(dftb_files), desc=f"Batch {batch}")
        )

    # salva CSV parziale
    df_batch = pd.DataFrame([r for r in batch_results if r])
    df_batch.to_csv(f"dataset_batch_{batch}.csv", index=False)

    results.extend(df_batch.to_dict(orient="records"))

# salva dataset completo
df = pd.DataFrame(sorted(results, key=lambda x: x["file_name"]))
df.to_csv("dataset.csv", index=False)
