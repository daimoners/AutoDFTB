try:
    from pathlib import Path
    from lib.electrodes_lib import (
        generate_electrode,
        adjust_outliers_atoms,
        check_interface_num_atoms,
        get_electrode,
        check_geometry_convergence,
    )
    from lib.dftb_lib import prepare_dftbplus_input
    from lib.poscar_lib import xyz_to_poscar
    from lib.utils_lib import get_cell_from_gen, launch_bin, check_dir, check_file
    import hydra
    from tqdm import tqdm
    import os
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

    files = [f for f in xyz_dir.iterdir() if f.suffix.lower() == ".xyz"]
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
    fixed_path = Path(args.xyz_dir_fixed)
    fixed_path.mkdir(exist_ok=True, parents=True)
    electrodes_path = Path(args.electrodes_dir)
    electrodes_path.mkdir(exist_ok=True, parents=True)
    box_size = args.box_size
    bond_lenght = args.bond_lenght
    delta_x = args.delta_x
    delta_y = args.delta_y
    delta_interface = args.delta_interface
    x_len = args.x_len
    y_len = args.y_len
    type = args.type

    adjust_outliers_atoms(
        file,
        working_dir.joinpath(f"{file.stem}_fixed.xyz"),
        cell_x=box_size[0],
        cell_y=box_size[4],
        delta_x=delta_x,
        delta_y=delta_y,
    )

    xyz_to_poscar(
        working_dir.joinpath(f"{file.stem}_fixed.xyz"),
        working_dir.joinpath(f"{file.stem}_fixed.POSCAR"),
        default_box_size=box_size,
    )
    prepare_dftbplus_input(args, working_dir.joinpath(f"{file.stem}_fixed.POSCAR"))
    launch_bin(dftb_bin_path, working_dir, verbose=args.verbose)
    shutil.copy(
        working_dir.joinpath(f"opt_{file.stem}_fixed.xyz"),
        fixed_path.joinpath(f"{file.stem}_fixed.xyz"),
    )
    box_size = get_cell_from_gen(
        working_dir.joinpath(f"opt_{file.stem}_fixed.gen"),
    )
    if not check_geometry_convergence(
        Path(args.package_path).joinpath(args.slurm_output, file.stem)
    ):
        print(f"Warning, Geometry did NOT converge for {file.stem}!")
        # os.remove(str(fixed_path.joinpath(f"{file.stem}_fixed.xyz")))
        # return

    if not check_interface_num_atoms(
        fixed_path.joinpath(f"{file.stem}_fixed.xyz"),
        cell_y=box_size[4],
        delta=delta_interface,
        bond_lenght=bond_lenght,
    ):
        os.remove(str(fixed_path.joinpath(f"{file.stem}_fixed.xyz")))
        return

    if not electrodes_path.joinpath("electrod.xyz").is_file():
        get_electrode(
            electrodes_path.joinpath("electrod.xyz"),
            x_len=x_len,
            y_len=y_len,
            type=type,
        )

    generate_electrode(
        fixed_path.joinpath(f"{file.stem}_fixed.xyz"),
        electrodes_path.joinpath(f"{file.stem}_e.xyz"),
        electrodes_path.joinpath("electrod.xyz"),
        cell=box_size,
        bond_lenght=bond_lenght,
    )
    shutil.rmtree(working_dir)


if __name__ == "__main__":
    main()
