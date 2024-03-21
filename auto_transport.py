try:
    from pathlib import Path
    import os
    import subprocess
    from dataclasses import dataclass
    import shutil
    from icecream import ic
    import hydra
    from tqdm import tqdm
    from lib.utils_lib import xyz2gen
    from lib.transport_lib import prepare_setupgeom_input
    from lib.dftb_lib import prepare_contact_input, prepare_transport_input
    from omegaconf import open_dict
    import submitit
    import json

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SLURM_AutoDFTB:
    def __init__(self, args):
        self.args = args

    def __call__(self):
        transport(self.args)


def launch_bin(
    bin_path: Path,
    working_dir: Path,
    verbose: bool = True,
    write_out_file: Path = None,
):
    os.chdir(str(working_dir))
    if write_out_file is None:
        process = subprocess.Popen(
            [str(bin_path)],
            shell=True,
            stdout=subprocess.PIPE if not verbose else None,
            stderr=subprocess.PIPE if not verbose else None,
        )
        process.wait()
    else:
        with open(str(write_out_file), "w") as output_file:
            process = subprocess.Popen(
                [str(bin_path)],
                shell=True,
                stdout=output_file,
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


@hydra.main(version_base="1.2", config_path="config", config_name="transport")
def main(args):
    if args.verbose:
        ic.enable()
    else:
        ic.disable()

    # TODO manca la parte di generazione degli elettrodi in xyz con i relativi files json

    xyz_dir = Path(args.xyz_dir)
    check_dir(xyz_dir)
    working_dir = Path(args.working_dir)
    gen_dir = Path(args.gen_dir)
    gen_dir.mkdir(exist_ok=True, parents=True)
    box_size = (
        [100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0, 100.0]
        if (not args.periodic and not args.box_size)
        else args.box_size
    )

    # === Convert xyz files to gen files === #
    ic("Converting xyz files to gen files...")
    files = [f for f in xyz_dir.iterdir() if f.suffix.lower() == ".xyz"]
    for file in tqdm(files):
        xyz2gen(
            file,
            gen_dir.joinpath(f"{file.stem}.gen"),
            cell=[box_size[0], box_size[4], box_size[8]],
        )
        shutil.copy(file.with_suffix(".json"), gen_dir.joinpath(f"{file.stem}.json"))

    # === Start DFTB+ simulations === #
    files = [f for f in gen_dir.iterdir() if f.suffix.lower() == ".gen"]
    ic(f"Submitting {len(files)} simulations...")
    for file in files:
        setupgeom_working_dir = working_dir.joinpath(f"{file.stem}_setupgeom")
        setupgeom_working_dir.mkdir(exist_ok=True, parents=True)
        contact_working_dir = working_dir.joinpath(f"{file.stem}_contact")
        contact_working_dir.mkdir(exist_ok=True, parents=True)
        transport_working_dir = working_dir.joinpath(f"{file.stem}_transport")
        transport_working_dir.mkdir(exist_ok=True, parents=True)
        with open_dict(args):
            args.setupgeom_working_dir = str(setupgeom_working_dir)
            args.contact_working_dir = str(contact_working_dir)
            args.transport_working_dir = str(transport_working_dir)
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


def transport(args):
    # === Get hydra config paths === #
    dftb_bin_path = Path(args.dftb_bin_path)
    setupgeom_bin_path = Path(args.setupgeom_bin_path)
    check_file(dftb_bin_path)
    check_file(setupgeom_bin_path)

    setupgeom_working_dir = Path(args.setupgeom_working_dir)
    contact_working_dir = Path(args.contact_working_dir)
    transport_working_dir = Path(args.transport_working_dir)
    file = Path(args.file)

    # === Prepare and run setupgeom input === #
    with open(str(file.with_suffix(".json")), "r") as f:
        data = json.load(f)

    with open_dict(args):
        args.atoms_source = data["source"]
        args.atoms_drain = data["drain"]
        args.contact_vector = [
            4.91,
            0.0,
            0.0,
        ]  # TODO funzione per ottenere il contact_vector

    ic(f"Prepare setupgeom for {file.name}...")
    shutil.copy(file, setupgeom_working_dir.joinpath(file.name))
    prepare_setupgeom_input(args, setupgeom_working_dir.joinpath(file.name))
    launch_bin(setupgeom_bin_path, setupgeom_working_dir, args.verbose)

    # === Prepare and run dftb+ input for source contact computation === #
    with open_dict(args):
        args.transport_file = setupgeom_working_dir.joinpath("transport.hsd")
        args.solver = "DivideAndConquer"

    shutil.copy(
        setupgeom_working_dir.joinpath("processed.gen"),
        contact_working_dir.joinpath("processed.gen"),
    )
    input_contact = prepare_contact_input(
        args, contact_working_dir.joinpath("processed.gen"), contact="source"
    )
    launch_bin(dftb_bin_path, contact_working_dir, args.verbose)

    # === Prepare and run dftb+ input for drain contact computation === #
    prepare_contact_input(
        args, contact_working_dir.joinpath("processed.gen"), contact="drain"
    )
    launch_bin(dftb_bin_path, contact_working_dir, args.verbose)

    # === Extract Fermi Levels === #
    with open(str(contact_working_dir.joinpath("shiftcont_source.dat")), "r") as f:
        lines = f.readlines()

    fermi_energy_source = float(lines[-1].split()[-2])

    with open(str(contact_working_dir.joinpath("shiftcont_drain.dat")), "r") as f:
        lines = f.readlines()

    fermi_energy_drain = float(lines[-1].split()[-2])

    # === Rebuild dftb_in.hsd === #
    fermi_string_source = f"FermiLevel [eV] = {fermi_energy_source:.2f}"
    fermi_string_drain = f"FermiLevel [eV] = {fermi_energy_drain:.2f}"
    potential_string_source = f"Potential [eV] = {args.potential_source}"
    potential_string_drain = f"Potential [eV] = -{args.potential_source}"

    closing_brace_index = input_contact.components["source"].rfind("}")
    input_contact.components["source"] = (
        input_contact.components["source"][:closing_brace_index]
        + f"\n    {fermi_string_source}\n    {potential_string_source}\n"
        + input_contact.components["source"][closing_brace_index:]
    )

    closing_brace_index = input_contact.components["drain"].rfind("}")
    input_contact.components["drain"] = (
        input_contact.components["drain"][:closing_brace_index]
        + f"\n    {fermi_string_drain}\n    {potential_string_drain}\n"
        + input_contact.components["drain"][closing_brace_index:]
    )

    # === Prepare and run dftb+ input for transport computation === #
    with open_dict(args):
        args.solver = "TransportOnly"
        args.tunnelinganddos.energy_range = [
            fermi_energy_drain - 0.1,
            fermi_energy_source + 0.1,
        ]

    shutil.copy(
        contact_working_dir.joinpath("processed.gen"),
        transport_working_dir.joinpath("processed.gen"),
    )
    prepare_transport_input(
        args,
        transport_working_dir.joinpath("processed.gen"),
        input_contact.components,
    )
    launch_bin(
        dftb_bin_path,
        transport_working_dir,
        args.verbose,
        write_out_file=transport_working_dir.joinpath("transport_output.out"),
    )

    # TODO parte per tirarsi fuori la corrente


if __name__ == "__main__":
    main()
