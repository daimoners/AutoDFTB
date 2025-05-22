try:
    from pathlib import Path
    from lib.electrodes_lib import (
        generate_electrode,
        adjust_outliers_atoms,
        check_interface_num_atoms,
        check_geometry_convergence,
    )
    from lib.dftb_lib import prepare_dftbplus_input
    from lib.poscar_lib import xyz_to_poscar
    from lib.utils_lib import (
        get_cell_from_gen,
        launch_bin,
        check_dir,
        check_file,
        translate_xyz_file,
        move_xyz_to_origin,
    )
    import hydra
    from tqdm import tqdm
    import os
    from icecream import ic
    import submitit
    import shutil
    from omegaconf import open_dict

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SLURM_Geometry:
    def __init__(self, args):
        self.args = args

    def __call__(self):
        optimize_geom(self.args)


@hydra.main(version_base="1.2", config_path="config", config_name="optimize_geometry")
def main(args):
    """
    Main entry point for geometry optimization.

    Depending on the scheduler type (slurm/local), distributes the xyz files 
    for DFTB+ optimization either locally or through a SLURM job scheduler.
    """
    
    if args.verbose:
        ic.enable()
    else:
        ic.disable()
    # ==== Old output clean =====#
    save_path = Path(args.package_path).joinpath(args.slurm_output)
    if save_path.exists():
        print(f"[INFO] Cleaning existing slurm output directory: {save_path}")
        shutil.rmtree(save_path)
    save_path.mkdir(parents=True, exist_ok=True)

    # === Get hydra config paths === #
    xyz_dir = Path(args.xyz_dir)
    check_dir(xyz_dir)
    working_dir = Path(args.working_dir)
    out_path = Path(args.xyz_dir_fixed)
    
    # === Filter already processed files === #
    if out_path.is_dir():
        already_done = [
            f.stem[:-4] for f in out_path.iterdir() if f.suffix.lower() == ".xyz"
        ]
        files = [
            f
            for f in xyz_dir.iterdir()
            if (f.suffix.lower() == ".xyz" and f.stem not in already_done)
        ]
    else:
        already_done = []
        files = [f for f in xyz_dir.iterdir() if f.suffix.lower() == ".xyz"]
        
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
    Processes all files locally by calling `optimize_geom()` sequentially.
    """
    for file in tqdm(files):
        local_working_dir = working_dir.joinpath(f"tmp_{file.stem}")
        local_working_dir.mkdir(exist_ok=True, parents=True)

        with open_dict(args):
            args.working_dir = str(local_working_dir)
            args.file = str(file)
        #Path(args.slurm_output).joinpath(file.stem).mkdir(parents=True, exist_ok=True)

        optimize_geom(args)
        
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
        slurm_auto_dftb = SLURM_Geometry(args)
        job = executor.submit(slurm_auto_dftb)
        print(f"Submitted job_id: {job.job_id}")

def optimize_geom(args):
    """
    Performs full geometry optimization workflow for a single xyz file.

    This includes:
    - Preparing the input (POSCAR, DFTB+ input)
    - Running DFTB+
    - Post-processing output files
    - Geometry validation and cleanup
    """
        
    dftb_bin_path = Path(args.dftb_bin_path)
    working_dir = Path(args.working_dir)
    file = Path(args.file)
    fixed_path = Path(args.xyz_dir_fixed)
    fixed_path.mkdir(exist_ok=True, parents=True)
    box_size = list(args.box_size)
    bond_lenght = args.bond_lenght
    delta_x = args.delta_x
    delta_y = args.delta_y
    delta_interface = args.delta_interface

    shutil.copy(file, working_dir.joinpath(file.name))

    xyz_to_poscar(
        working_dir.joinpath(file.name),
        working_dir.joinpath(f"{file.stem}.POSCAR"),
        default_box_size=box_size,
    )
    prepare_dftbplus_input(args, working_dir.joinpath(f"{file.stem}.POSCAR"))
    base_output_dir = Path(args.package_path).joinpath(args.slurm_output)
    base_output_dir.mkdir(exist_ok=True, parents=True)

    local_path = base_output_dir.joinpath(file.stem)
    local_path.mkdir(exist_ok=True, parents=True)
    print(f"Local path: {local_path}")
    
    if args.scheduler == "slurm":
        write_out_file = None
    elif args.scheduler == "local":
        write_out_file = str(local_path.joinpath(file.stem)) + ".out"
    else:
        raise ValueError(f"Scheduler {args.scheduler} not supported")
    
    launch_bin(dftb_bin_path, working_dir,write_out_file=write_out_file, verbose=args.verbose)
    shutil.copy(
        working_dir.joinpath(f"opt_{file.stem}.xyz"),
        fixed_path.joinpath(f"{file.stem}_opt.xyz"),
    )
    get_cell_from_gen(
        working_dir.joinpath(f"opt_{file.stem}.gen"),
        json_output_path=fixed_path.joinpath(f"{file.stem}_opt.json"),
        custom_name=file.stem,
    )
    # === Check convergence === #

    if not check_geometry_convergence(
        Path(args.package_path).joinpath(args.slurm_output, file.stem)
    ):
        print(f"Warning, Geometry did NOT converge for {file.stem}!")
        if args.remove_if_not_converged:
            os.remove(str(fixed_path.joinpath(file.stem + "_opt.xyz")))
            os.remove(str(fixed_path.joinpath(f"{file.stem}_opt.json")))
            shutil.rmtree(working_dir)
            return

    translate_xyz_file(fixed_path.joinpath(f"{file.stem}_opt.xyz"), z_offset=-5.0)
    move_xyz_to_origin(fixed_path.joinpath(f"{file.stem}_opt.xyz"))

    adjust_outliers_atoms(
        fixed_path.joinpath(f"{file.stem}_opt.xyz"),
        fixed_path.joinpath(f"{file.stem}_opt.xyz"),
        cell_x=box_size[0],
        cell_y=box_size[4],
        delta_x=delta_x,
        delta_y=delta_y,
    )

    if not check_interface_num_atoms(
        fixed_path.joinpath(f"{file.stem}_opt.xyz"),
        cell_y=box_size[4],
        delta=delta_interface,
        bond_lenght=bond_lenght,
    ):
        os.remove(str(fixed_path.joinpath(f"{file.stem}_opt.xyz")))
        os.remove(str(fixed_path.joinpath(f"{file.stem}_opt.json")))
        shutil.rmtree(working_dir)
        return

    shutil.rmtree(working_dir)


if __name__ == "__main__":
    main()
