try:
    from pathlib import Path
    import random
    from lib.utils_lib import Utils
    from tqdm.rich import tqdm
    import cv2
    import numpy as np
    import shutil

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


def main(n_batch: int, threshold: float = 0.085):
    max_dim = [39.53476932, 34.27629786]
    tmp = Path().cwd().joinpath("tmp")
    tmp.mkdir(exist_ok=True, parents=True)
    xyz_files_total_path = Path().home().joinpath("xyz_files_G")
    package_path = Path().cwd()
    batches_dir = [
        f for f in package_path.iterdir() if (f.is_dir() and "data_batch" in f.stem)
    ]
    total_samples = []
    for batch in batches_dir:
        samples = [
            f.stem
            for f in batch.joinpath("xyz_files").iterdir()
            if f.suffix.lower() == ".xyz"
        ]
        total_samples = [*total_samples, *samples]
        samples.clear()

    new_samples = [
        f
        for f in xyz_files_total_path.iterdir()
        if (f.suffix.lower() == ".xyz" and f.stem not in total_samples)
    ]
    random.shuffle(new_samples)

    out_path = Path().cwd().joinpath(f"data_batch_{n_batch}", "xyz_files")
    out_path.mkdir(parents=True)

    count = 0
    pbar = tqdm(total=5000)
    for sample in new_samples:
        Utils.generate_bonds_png(sample, tmp, max_dim, multiplier=6)

        if check_defects_size(tmp.joinpath(f"{sample.stem}.png")) > threshold:
            shutil.copy(sample, out_path.joinpath(sample.name))

            count += 1
            pbar.update(1)
            pbar.refresh()

        if count >= 5000:
            break

    pbar.close()
    shutil.rmtree(tmp)


def check_defects_size(img_path: Path) -> float:
    img = cv2.imread(str(img_path))

    non_black_mask = np.any(img != [0, 0, 0], axis=-1)

    non_black_pixel_count = np.sum(non_black_mask)

    if len(img.shape) == 2:
        h, w = img.shape
    elif len(img.shape) == 3:
        h, w, _ = img.shape

    return non_black_pixel_count / (h * w)


if __name__ == "__main__":
    main(n_batch=2)
    # print(
    #     check_defects_size(
    #         Path("/home/tommaso/git_workspace/AutoDFTB/tmp/graphene_15228.png")
    #     )
    # )

    # print(
    #     check_defects_size(
    #         Path("/home/tommaso/git_workspace/AutoDFTB/tmp/graphene_539160.png")
    #     )
    # )

    # print(
    #     check_defects_size(
    #         Path("/home/tommaso/git_workspace/AutoDFTB/tmp/graphene_244741.png")
    #     )
    # )
