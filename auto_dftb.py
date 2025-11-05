try:
    from pathlib import Path
    import submitit
    import hydra
    from tqdm import tqdm
    from lib.poscar_lib import xyz_to_poscar
    from lib.utils_lib import (
        get_poscar_data,
        get_results,
        check_dir,
        check_file,
        launch_bin,
        submit_with_retry
    )
    from lib.dftb_lib import prepare_dftbplus_input
    import shutil
    import os
    import subprocess
    import json
    from icecream import ic
    from omegaconf import open_dict, OmegaConf

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SLURM_AutoDFTB:
    def __init__(self, args):
        self.args = args

    def __call__(self):
        dftb(self.args)


@hydra.main(version_base="1.2", config_path="config", config_name="dftb")
def main(args):
    if args.verbose:
        ic.enable()
    else:
        ic.disable()
    save_path = Path(args.package_path).joinpath(args.slurm_output)
    if save_path.exists():
        print(f"[INFO] Cleaning existing slurm output directory: {save_path}")
        shutil.rmtree(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    xyz_dir = Path(args.xyz_dir)
    check_dir(xyz_dir)
    working_dir = Path(args.working_dir)
    poscar_dir = Path(args.poscar_dir)
    poscar_dir.mkdir(exist_ok=True, parents=True)
    box_size = (
        [100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0, 100.0]
        if (not args.periodic and not args.box_size)
        else args.box_size
    )

    # === Convert xyz files to POSCAR files === #
    ic("Converting xyz files to POSCAR files...")
    json_dir = Path(args.json_dir)
    if json_dir.is_dir():
        already_done = [
            f.stem for f in json_dir.iterdir() if f.suffix.lower() == ".json"
        ]
        files = [
            f
            for f in xyz_dir.iterdir()
            if (f.suffix.lower() == ".xyz" and f.stem not in already_done)
        ]
    else:
        already_done = []
        files = [f for f in xyz_dir.iterdir() if f.suffix.lower() == ".xyz"]

    for file in tqdm(files):
        xyz_to_poscar(file, poscar_dir.joinpath(f"{file.stem}.POSCAR"), box_size)

    # === Start DFTB+ simulations === #
    files = [
        f
        for f in poscar_dir.iterdir()
        if (f.suffix.lower() == ".poscar" and f.stem not in already_done)
    ]
    ic(f"Submitting {len(files)} simulations...")
    
    # === Choose execution strategy === #
    if args.scheduler == "slurm":
        run_slurm(files, args, working_dir)
    elif args.scheduler == "local":
        run_local(files, args, working_dir)
    else:
        print(f"Scheduler '{args.scheduler}' not recognized. Valid options: [slurm, local]")
        return

def run_local(files, args, working_dir):
    """
    Processes all files locally by calling `dftb()` sequentially.
    """
    for file in tqdm(files):
        local_working_dir = working_dir.joinpath(f"tmp_{file.stem}")
        local_working_dir.mkdir(exist_ok=True, parents=True)
        with open_dict(args):
            args.working_dir = str(local_working_dir)
            args.file = str(file)

        dftb(args)

def run_slurm(files, args, working_dir):
    """
    Submits DFTB+ jobs using SLURM via submitit.
    Each POSCAR file is submitted as an individual job.
    """    
    failed = []  # lista di tuple (file, original_args_snapshot)
    submitted_jobs = []
    for file in tqdm(files):
        local_working_dir = working_dir.joinpath(f"tmp_{file.stem}")
        local_working_dir.mkdir(exist_ok=True, parents=True)
        with open_dict(args):
            args.working_dir = str(local_working_dir)
            args.file = str(file)

        Path(args.slurm_output).joinpath(file.stem).mkdir(parents=True, exist_ok=True)
        executor = submitit.AutoExecutor(
            folder=str(Path(args.slurm_output).joinpath(file.stem)),
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
        try:
            job = submit_with_retry(executor, slurm_auto_dftb)
            print(f"Submitted job_id: {job.job_id}")
            submitted_jobs.append((file,job))
        except Exception as e:
            print(f"Failed to submit {file.name} after retries: {e}")
            failed.append((file,  OmegaConf.to_container(args, resolve=True)))

    if failed:
        print("\nRetrying failed submissions with fallback adjustments...")
    retry_failed = []
    for file, saved_args in tqdm(failed, desc="Retry failed"):
     
        with open_dict(args):
            for k, v in saved_args.items():
                setattr(args, k, v)
        local_working_dir = Path(args.working_dir) 
        out_dir = Path(args.slurm_output).joinpath(file.stem)
        executor = submitit.AutoExecutor(folder=str(out_dir), slurm_max_num_timeout=30)

        # fallback: riduci risorse (esempio: metà cpu e memoria, minimo 1)
        base_mem = 0 if not args.slurm_mem else args.slurm_mem
        base_cpus = 2 if not args.slurm_ncpus else args.slurm_ncpus


        executor.update_parameters(
            mem_gb=base_mem if base_cpus is not None else 0,
            tasks_per_node=1,
            cpus_per_task=base_cpus,
            timeout_min=args.slurm_timeout,
            slurm_partition=args.slurm_partition,
            slurm_exclude=args.slurm_exclude,
        )
        if args.slurm_nodelist:
            executor.update_parameters(
                slurm_additional_parameters={"nodelist": f"{args.slurm_nodelist}"}
            )
        executor.update_parameters(name=f"{args.slurm_job_name}_{file.stem}_fallback")

        slurm_auto_dftb = SLURM_AutoDFTB(args)
        try:
            job = submit_with_retry(executor, slurm_auto_dftb)
            print(f"[fallback ok] Submitted job_id: {job.job_id} for {file.name}")
            submitted_jobs.append((file, job))
        except Exception as e:
            print(f"[error] Fallback submission also failed for {file.name}: {e}")
            retry_failed.append((file, str(e)))

    # Recap of 2 turn failed job
    if retry_failed:
        print("\nSummary of permanently failed submissions:")
        for file, err in retry_failed:
            print(f" - {file.name}: {err}")
    else:
        print("\nAll failed submissions were recovered or retried.")

def dftb(args):
    # === Get hydra config paths === #
    dftb_bin_path = Path(args.dftb_bin_path)
    check_file(dftb_bin_path)
    json_dir = Path(args.json_dir)
    json_dir.mkdir(exist_ok=True, parents=True)
    working_dir = Path(args.working_dir)
    file = Path(args.file)

    # === Start DFTB+ simulations === #
    
    # === Prepare and launch E0 simulation === #
    ic(f"Prepare and launch E0 simulation for {file.name}...")
    shutil.copy(file, working_dir.joinpath(file.name))
    prepare_dftbplus_input(args, working_dir.joinpath(file.name))
    launch_bin(dftb_bin_path, working_dir, args.verbose)

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
    with open_dict(args):
        args.charge = -1
    prepare_dftbplus_input(args, working_dir.joinpath(file.name))
    launch_bin(dftb_bin_path, working_dir, args.verbose)

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
    with open_dict(args):
        args.charge = +1
    prepare_dftbplus_input(args, working_dir.joinpath(file.name))
    launch_bin(dftb_bin_path, working_dir, args.verbose)

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
    # results["band_gap_ev"] = float(results["total_energy_eV_-1"]) + float(
    #     results["total_energy_eV_+1"]
    # )
    E0 = float(results["total_energy_eV"])
    E_minus = float(results["total_energy_eV_-1"])
    E_plus = float(results["total_energy_eV_+1"])

    results["IP_ev"] = E_minus - E0
    results["EA_ev"] = E0 - E_plus
    results["band_gap_ev"] = E_minus - 2 * E0 + E_plus

    # results["band_gap_ev"] = (
    #     float(results["total_energy_eV_-1"])
    #     - 2 * float(results["total_energy_eV"])
    #     + float(results["total_energy_eV_+1"])
    # )

    # === Clear the working directory === #
    shutil.rmtree(working_dir)

    ic("\nDone\n")

    with open(str(json_dir.joinpath(f"{file.stem}.json")), "w") as f:
        json.dump(results, f, indent=4)


if __name__ == "__main__":
    main()
