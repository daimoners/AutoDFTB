try:
    import shutil
    from pathlib import Path
    import random
    from tqdm.rich import tqdm

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


def copy_n_samples(source_dir: Path, dest_dir: Path, n: int):

    dest_dir.mkdir(parents=True, exist_ok=True)

    all_files = [f.stem for f in source_dir.iterdir() if f.suffix.lower() == ".xyz"]

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
        "/home/tommaso/git_workspace/AutoDFTB/data/transport/electrodes_test"
    )
    num_samples = 500

    copy_n_samples(source_folder, destination_folder, num_samples)
