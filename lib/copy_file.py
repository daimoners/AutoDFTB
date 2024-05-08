try:
    import shutil
    from pathlib import Path
    import random
    from tqdm.rich import tqdm

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


def copy_n_samples(source_dir: Path, dest_dir: Path, n: int, check_dir: Path = None):

    dest_dir.mkdir(parents=True, exist_ok=True)

    all_files = [f.stem for f in source_dir.iterdir() if f.suffix.lower() == ".xyz"]

    if check_dir is not None:
        check_files = [
            f.stem for f in check_dir.iterdir() if f.suffix.lower() == ".xyz"
        ]

        all_files = [elemento for elemento in all_files if elemento not in check_files]

    files_to_copy = random.sample(all_files, n)

    for file in tqdm(files_to_copy):
        shutil.copy(
            source_dir.joinpath(f"{file}.xyz"), dest_dir.joinpath(f"{file}.xyz")
        )
        shutil.copy(
            source_dir.joinpath(f"{file}.json"), dest_dir.joinpath(f"{file}.json")
        )


if __name__ == "__main__":
    source_folder = Path(
        "/home/tommaso/git_workspace/AutoDFTB/data/transport/electrodes"
    )
    destination_folder = Path(
        "/home/tommaso/git_workspace/AutoDFTB/data/transport/electrodes_test2"
    )
    num_samples = 500
    check_dir = Path(
        "/home/tommaso/git_workspace/AutoDFTB/data/transport/electrodes_test"
    )

    copy_n_samples(source_folder, destination_folder, num_samples, check_dir)
