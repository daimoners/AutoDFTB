try:
    from pathlib import Path
    from lib.electrodes_lib import (
        generate_electrode,
        check_geometry_convergence,
    )
    from lib.dftb_lib import prepare_dftbplus_input
    from lib.poscar_lib import xyz_to_poscar
    from lib.utils_lib import (
        launch_bin,
        check_dir,
        check_file,
        translate_xyz_file,
        move_xyz_to_origin,
    )
    import hydra
    from tqdm.rich import tqdm
    from icecream import ic
    import submitit
    import shutil
    from omegaconf import open_dict

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SLURM_Transport:
    def __init__(self, args):
        self.args = args

    def __call__(self):
        generate_transport_devices(self.args)


@hydra.main(version_base="1.2", config_path="config", config_name="electrodes")
def main(args):
    if args.verbose:
        ic.enable()
    else:
        ic.disable()

    # === Get hydra config paths === #
    xyz_dir = Path(args.xyz_dir)
    check_dir(xyz_dir)
    working_dir = Path(args.working_dir)

    electrodes_dir = Path(args.electrodes_dir)

    if electrodes_dir.is_dir():
        already_done = [
            f.stem[:-2] for f in electrodes_dir.iterdir() if f.suffix.lower() == ".json"
        ]
        files = [
            f
            for f in xyz_dir.iterdir()
            if (f.suffix.lower() == ".xyz" and f.stem not in already_done)
        ]
    else:
        files = [f for f in xyz_dir.iterdir() if f.suffix.lower() == ".xyz"]

    if args.scheduler == "slurm":
        run_slurm(files, args, working_dir)
    elif args.scheduler == "local":
        run_local(files, args, working_dir)
    else:
        print(f"Scheduler '{args.scheduler}' not recognized. Valid options: [slurm, local]")
        return

def run_local(files, args, working_dir):
    """
    Processes all files locally by calling `optimize_geom()` sequentially.
    """
    for file in tqdm(files):
        local_working_dir = working_dir.joinpath(f"tmp_{file.stem}")
        local_working_dir.mkdir(exist_ok=True, parents=True)
        with open_dict(args):
            args.working_dir = str(local_working_dir)
            args.file = str(file)

        generate_transport_devices(args)

def run_slurm(files, args, working_dir):
    """
    Submits geometry optimization jobs using SLURM via submitit.
    Each xyz file is submitted as an individual job.
    """
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
        slurm_auto_dftb = SLURM_Transport(args)
        job = executor.submit(slurm_auto_dftb)
        print(f"Submitted job_id: {job.job_id}")

def generate_transport_devices(args):
    # === Get hydra config paths === #
    dftb_bin_path = Path(args.dftb_bin_path)
    working_dir = Path(args.working_dir)
    file = Path(args.file)
    electrodes_path = Path(args.electrodes_dir)
    electrodes_path.mkdir(exist_ok=True, parents=True)
    box_size = list(args.box_size)
    electrode_path = args.electrode_path
    electrode_cell = args.electrode_cell

    shutil.copy(file, working_dir.joinpath(file.name))

    atom_range = generate_electrode(
        working_dir.joinpath(file.name),
        working_dir.joinpath(f"{file.stem}_e.xyz"),
        Path(electrode_path),
        cell=box_size,
        contact_vector=float(electrode_cell[0]),
    )

    box_size[0] += 2 * electrode_cell[0]
    with open_dict(args):
        args.box_size = box_size

    xyz_to_poscar(
        working_dir.joinpath(f"{file.stem}_e.xyz"),
        working_dir.joinpath(f"{file.stem}_e.POSCAR"),
        default_box_size=box_size,
    )
    with open_dict(args):
        args.moved_atoms = atom_range["device"]
    prepare_dftbplus_input(args, working_dir.joinpath(f"{file.stem}_e.POSCAR"))
    launch_bin(dftb_bin_path, working_dir, verbose=args.verbose)
    if not check_geometry_convergence(
        Path(args.package_path).joinpath(args.slurm_output, file.stem)
    ):
        print(f"Warning, Geometry did NOT converge for {file.stem}!")
        if args.remove_if_not_converged:
            shutil.rmtree(working_dir)
            return
    else:
        translate_xyz_file(
            working_dir.joinpath(f"opt_{file.stem}_e.xyz"), z_offset=-5.0
        )
        move_xyz_to_origin(working_dir.joinpath(f"opt_{file.stem}_e.xyz"))

        shutil.copy(
            working_dir.joinpath(f"opt_{file.stem}_e.xyz"),
            electrodes_path.joinpath(f"{file.stem}_e.xyz"),
        )
        shutil.copy(
            working_dir.joinpath(f"opt_{file.stem}_e.gen"),
            electrodes_path.joinpath(f"{file.stem}_e.gen"),
        )
        shutil.copy(
            working_dir.joinpath(f"{file.stem}_e.json"),
            electrodes_path.joinpath(f"{file.stem}_e.json"),
        )

    shutil.rmtree(working_dir)


if __name__ == "__main__":
    main()
