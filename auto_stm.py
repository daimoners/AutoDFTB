try:
    from pathlib import Path
    from lib.utils_lib import (
        check_dir,
        check_file,
    )
    import hydra
    from tqdm.rich import tqdm
    from icecream import ic
    import submitit
    from omegaconf import open_dict
    from lib.stm_lib import StmSimulator
    import json

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SLURM_STM:
    def __init__(self, args):
        self.args = args

    def __call__(self):
        generate_stm_images(self.args)


@hydra.main(version_base="1.2", config_path="config", config_name="stm")
def main(args):
    if args.verbose:
        ic.enable()
    else:
        ic.disable()

    # === Get hydra config paths === #
    xyz_dir = Path(args.xyz_dir)
    check_dir(xyz_dir)
    json_dir = Path(args.json_dir)
    check_dir(json_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True, parents=True)

    files = [f for f in xyz_dir.iterdir() if f.suffix.lower() == ".xyz"]
    for file in tqdm(files):
        check_file(file)
        check_file(json_dir.joinpath(f"{file.stem}.json"))

        with open_dict(args):
            args.xyz_file = str(file)
            args.json_file = str(json_dir.joinpath(f"{file.stem}.json"))

        if args.slurm:
            Path(args.slurm_output).joinpath(file.stem).mkdir(
                parents=True, exist_ok=True
            )
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
            slurm_auto_dftb = SLURM_STM(args)
            job = executor.submit(slurm_auto_dftb)
            print(f"Submitted job_id: {job.job_id}")

        else:
            generate_stm_images(args)


def generate_stm_images(args):
    xyz_file = Path(args.xyz_file)
    json_file = Path(args.json_file)

    with open(str(json_file), "r") as f:
        data = json.load(f)

    fermi_energy_source = float(data["fermi_energy_source"])
    fermi_energy_drain = float(data["fermi_energy_drain"])
    fermi_energy = (fermi_energy_source + fermi_energy_drain) / 2

    atoms_device = list(data["atoms_device"])

    stm = StmSimulator(
        xyz_path=xyz_file,
        dos_per_atom_path=json_file,
        fermi_level=fermi_energy,
        bias=args.bias,
        atoms_device=atoms_device,
    )
    img = stm.get_stm_img(
        image_res=(args.resolution, args.resolution), tau=args.tau, scan_h=args.scan_h
    )

    if args.save_npy:
        stm.save_npy(img, Path(args.out_dir).joinpath(f"{xyz_file.stem}.npy"))
    if args.save_png:
        stm.save_png(-img, Path(args.out_dir).joinpath(f"{xyz_file.stem}.png"))


if __name__ == "__main__":
    main()
