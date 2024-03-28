try:
    from pathlib import Path
    import shutil
    from icecream import ic
    import hydra
    from tqdm import tqdm
    from lib.utils_lib import (
        xyz2gen,
        launch_bin,
        check_dir,
        check_file,
        get_current_value,
    )
    from lib.transport_lib import prepare_setupgeom_input, get_regions_dict
    from lib.dftb_lib import prepare_contact_input, prepare_transport_input
    from omegaconf import open_dict
    import submitit
    import json
    import pandas as pd

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SLURM_AutoDFTB:
    def __init__(self, args):
        self.args = args

    def __call__(self):
        transport(self.args)


@hydra.main(version_base="1.2", config_path="config", config_name="transport")
def main(args):
    if args.verbose:
        ic.enable()
    else:
        ic.disable()

    electrodes_dir = Path(args.electrodes_dir)
    check_dir(electrodes_dir)
    working_dir = Path(args.working_dir)
    gen_dir = Path(args.gen_dir)
    gen_dir.mkdir(exist_ok=True, parents=True)
    transport_output = Path(args.transport_output)
    transport_output.mkdir(exist_ok=True, parents=True)
    box_size = (
        [100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0, 100.0]
        if (not args.periodic and not args.box_size)
        else args.box_size
    )

    # === Convert xyz files to gen files === #
    ic("Converting xyz files to gen files...")
    files = [f for f in electrodes_dir.iterdir() if f.suffix.lower() == ".xyz"]
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
    electrode_cell = list(args.electrode_cell)
    transport_output = Path(args.transport_output)

    # === Prepare and run setupgeom input === #
    with open(str(file.with_suffix(".json")), "r") as f:
        data = json.load(f)

    with open_dict(args):
        args.atoms_device = data["device"]
        args.atoms_source = data["source"]
        args.atoms_drain = data["drain"]
        args.contact_vector = [
            electrode_cell[0],
            0.0,
            0.0,
        ]

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
            fermi_energy_drain - args.tunnelinganddos.offset_energy_range,
            fermi_energy_source + args.tunnelinganddos.offset_energy_range,
        ]
        args.tunnelinganddos.energy_step = (
            2
            * args.tunnelinganddos.offset_energy_range
            / args.tunnelinganddos.resolution
        )

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

    # === Prepare JSON ouput === #
    current = get_current_value(
        transport_working_dir.joinpath("transport_output.out"),
        transport_working_dir.joinpath(f"{file.stem}.json"),
    )

    data = {
        "file_name": file.stem,
        "current": current,
        "transport_cell": list(args.box_size),
        "contact_vector": list(args.contact_vector),
        "potential_source": args.potential_source,
        "potential_drain": args.potential_drain,
        "energy_range": list(args.tunnelinganddos.energy_range),
        "energy_step": args.tunnelinganddos.energy_step,
        "fermi_temperature": args.fermi_temperature,
    }

    data["LDOS"] = get_regions_dict(transport_working_dir)

    with open(str(transport_working_dir.joinpath(f"{file.stem}.json")), "w") as f:
        json.dump(data, f, indent=4)
    shutil.copy(
        transport_working_dir.joinpath(f"{file.stem}.json"),
        transport_output.joinpath(f"{file.stem}.json"),
    )

    shutil.rmtree(transport_working_dir)
    shutil.rmtree(setupgeom_working_dir)
    shutil.rmtree(contact_working_dir)


if __name__ == "__main__":
    main()
    # spath = Path("/home/tommaso/git_workspace/AutoDFTB/data/transport/electrodes")
    # dpath = Path("/home/tommaso/git_workspace/AutoDFTB/data/transport/electrodes_test")
    # dpath.mkdir(exist_ok=True, parents=True)
    # files = [f for f in spath.iterdir() if f.suffix.lower() == ".xyz"]
    # files = sorted(files, key=lambda x: str(x))[:1000]
    # for file in tqdm(files):
    #     shutil.copy(file, dpath.joinpath(file.name))
    #     shutil.copy(file.with_suffix(".json"), dpath.joinpath(f"{file.stem}.json"))
