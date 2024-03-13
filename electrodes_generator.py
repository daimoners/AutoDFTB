try:
    from pathlib import Path
    from lib.electrodes_lib import (
        generate_electrode,
        adjust_outliers_atoms,
        check_interface_num_atoms,
        get_electrode,
    )
    import hydra
    from tqdm import tqdm
    import os
    from icecream import ic
    import submitit
    import shutil

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SLURM_Transport:
    def __init__(self, args):
        self.args = args

    def __call__(self):
        generate_transport_devices(self.args)


@hydra.main(version_base="1.2", config_path="config", config_name="transport")
def main(args):
    if args.verbose:
        ic.enable()
    else:
        ic.disable()

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

    executor.update_parameters(name=f"{args.slurm_job_name}")
    slurm_auto_dftb = SLURM_Transport(args)
    job = executor.submit(slurm_auto_dftb)
    print(f"Submitted job_id: {job.job_id}")


def generate_transport_devices(args):
    xyz_files = Path(args.xyz_dir)
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

    samples = [f for f in xyz_files.iterdir() if f.suffix.lower() == ".xyz"]
    for sample in tqdm(samples):
        adjust_outliers_atoms(
            sample,
            fixed_path.joinpath(f"{sample.stem}_fixed.xyz"),
            cell_x=box_size[0],
            cell_y=box_size[4],
            delta_x=delta_x,
            delta_y=delta_y,
        )

    samples = [f for f in fixed_path.iterdir() if f.suffix.lower() == ".xyz"]
    for sample in tqdm(samples):
        if not check_interface_num_atoms(
            sample, cell_y=box_size[4], delta=delta_interface, bond_lenght=bond_lenght
        ):
            os.remove(str(sample))

    get_electrode(
        electrodes_path.joinpath("electrod.xyz"), x_len=x_len, y_len=y_len, type=type
    )

    samples = [f for f in fixed_path.iterdir() if f.suffix.lower() == ".xyz"]
    for sample in tqdm(samples):
        generate_electrode(
            sample,
            electrodes_path.joinpath(f"{sample.stem}_e.xyz"),
            electrodes_path.joinpath("electrod.xyz"),
            cell_x=box_size[0],
            bond_lenght=bond_lenght,
        )
    ic(f"{len(samples)} devices were generated!")

    if args.remove_fixeds_when_finished:
        shutil.rmtree(fixed_path)


if __name__ == "__main__":
    main()
