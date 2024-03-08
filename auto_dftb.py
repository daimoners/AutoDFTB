try:
    from pathlib import Path
    import submitit
    import hydra
    from tqdm import tqdm
    from lib.poscar_lib import xyz_to_poscar
    from lib.dftb_lib import prepare_dftbplus_input, get_poscar_data, get_results
    import shutil
    import os
    import subprocess
    import json
    from icecream import ic
    from omegaconf import open_dict

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SLURM_AutoDFTB:
    def __init__(self, args):
        self.args = args

    def __call__(self):
        dftb(self.args)


def launch_dftb(dftb_bin_path: Path, working_dir: Path, verbose: bool = True):
    os.chdir(str(working_dir))
    process = subprocess.Popen(
        [str(dftb_bin_path)],
        shell=True,
        stdout=subprocess.PIPE if not verbose else None,
        stderr=subprocess.PIPE if not verbose else None,
    )
    process.wait()
    os.chdir(str(Path().resolve()))


def clear_working_dir(working_dir: Path):
    shutil.rmtree(working_dir)


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


@hydra.main(version_base="1.2", config_path="config", config_name="cfg")
def main(args):
    if args.verbose:
        ic.enable()
    else:
        ic.disable()

    xyz_dir = Path(args.xyz_dir)
    check_dir(xyz_dir)
    working_dir = Path(args.working_dir)
    poscar_dir = Path(args.poscar_dir)
    poscar_dir.mkdir(exist_ok=True, parents=True)
    box_size = (
        [100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0, 100.0]
        if not args.box_size
        else args.box_size
    )

    # === Convert xyz files to POSCAR files === #
    ic("Converting xyz files to POSCAR files...")
    files = [f for f in xyz_dir.iterdir() if f.suffix.lower() == ".xyz"]
    for file in tqdm(files):
        xyz_to_poscar(file, poscar_dir.joinpath(f"{file.stem}.POSCAR"), box_size)

    # === Start DFTB+ simulations === #
    files = [f for f in poscar_dir.iterdir() if f.suffix.lower() == ".poscar"]
    ic(f"Submitting {len(files)} simulations...")
    for file in files:
        local_working_dir = working_dir.joinpath(f"{working_dir.stem}_{file.stem}")
        local_working_dir.mkdir(exist_ok=True, parents=True)
        with open_dict(args):
            args.working_dir = str(local_working_dir)
            args.file = str(file)

        Path(args.slurm_output).mkdir(parents=True, exist_ok=True)
        executor = submitit.AutoExecutor(
            folder=args.slurm_output,
            slurm_max_num_timeout=30,
        )

        executor.update_parameters(
            mem_gb=0 if not args.slurm_mem else args.slurm_mem,
            tasks_per_node=1,
            cpus_per_task=2 if not args.slurm_ncpus else args.slurm_ncpus,
            timeout_min=args.slurm_timeout,
            slurm_partition=args.slurm_partition,
            slurm_exclude=args.slurm_exclude,
        )

        if args.slurm_nodelist:
            executor.update_parameters(
                slurm_additional_parameters={"nodelist": f"{args.slurm_nodelist}"}
            )

        executor.update_parameters(name=f"{args.slurm_job_name}_{file.stem}")
        slurm_auto_dftb = SLURM_AutoDFTB(args)
        job = executor.submit(slurm_auto_dftb)
        print(f"Submitted job_id: {job.job_id}")


def dftb(args):
    # === Get hydra config paths === #
    dftb_bin_path = Path(args.dftb_bin_path)
    slakos = Path(args.slakos)
    check_file(dftb_bin_path)
    json_dir = Path(args.json_dir)
    json_dir.mkdir(exist_ok=True, parents=True)
    working_dir = Path(args.working_dir)
    file = Path(args.file)

    # === Start DFTB+ simulations === #

    # === Prepare and launch E0 simulation === #
    ic(f"Prepare and launch E0 simulation for {file.name}...")
    shutil.copy(file, working_dir.joinpath(file.name))
    prepare_dftbplus_input(working_dir.joinpath(file.name), slakos)
    launch_dftb(dftb_bin_path, working_dir, args.verbose)

    # === Get E0 simulation results === #
    ic(f"Get E0 simulation results for {file.name}...")
    values_to_find = [
        "Nr. of electrons (up):",
        "Total Electronic energy:",
        "Fermi level:",
    ]
    results = get_results(values_to_find, working_dir.joinpath("detailed.out"))
    results["file_name"] = file.stem
    results["file_type"] = file.suffix[1:]

    # === Prepare and launch E- simulation === #
    ic(f"Prepare and launch E- simulation for {file.name}...")
    prepare_dftbplus_input(working_dir.joinpath(file.name), slakos, charge=-1)
    launch_dftb(dftb_bin_path, working_dir, args.verbose)

    # === Get E- simulation results === #
    ic(f"Get E- simulation results for {file.name}...")
    values_to_find = ["Total Electronic energy:"]
    results = get_results(
        values_to_find,
        working_dir.joinpath("detailed.out"),
        found_values=results,
        charge="-1",
    )

    # === Prepare and launch E+ simulation === #
    ic(f"Prepare and launch E+ simulation for {file.name}...")
    prepare_dftbplus_input(working_dir.joinpath(file.name), slakos, charge=+1)
    launch_dftb(dftb_bin_path, working_dir, args.verbose)

    # === Get E+ simulation results === #
    ic(f"Get E+ simulation results for {file.name}...")
    values_to_find = ["Total Electronic energy:"]
    results = get_results(
        values_to_find,
        working_dir.joinpath("detailed.out"),
        found_values=results,
        charge="+1",
    )

    # === Compute IP, EA and band_gap === #
    ic(f"Compute IP, EA and band_gap for {file.name}...")
    results["IP_ev"] = float(results["total_energy_eV"]) - float(
        results["total_energy_eV_-1"]
    )
    results["EA_ev"] = float(results["total_energy_eV"]) - float(
        results["total_energy_eV_+1"]
    )
    results["band_gap_ev"] = float(results["total_energy_eV_-1"]) - float(
        results["total_energy_eV_+1"]
    )

    # === Clear the working directory === #
    clear_working_dir(working_dir)

    ic("\nDone\n")

    with open(str(json_dir.joinpath(f"{file.stem}.json")), "w") as f:
        json.dump(results, f, indent=4)


if __name__ == "__main__":
    main()
