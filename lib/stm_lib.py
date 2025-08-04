try:
    from pathlib import Path
    import numpy as np
    import json
    from numba import jit
    import matplotlib.pyplot as plt
    import cv2
    from skimage import exposure
except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class StmSimulator:
    def __init__(
        self,
        xyz_path: Path,
        dos_per_atom_path: Path,
        bias: float,
        fermi_level: float,
        atoms_device: list = None,
    ) -> None:

        # self.__check_dir(xyz_path)
        # self.__check_dir(dos_per_atom_path)
        # self.__check_exists(xyz_path)
        # self.__check_exists(dos_per_atom_path)

        self.xyz_path = xyz_path
        self.dos_per_atom_path = dos_per_atom_path
        self.bias = bias
        self.fermi_level = fermi_level
        self.atoms_device = atoms_device

    def __check_dir(self, path: Path) -> "bool":
        """
        Check if the specified directory is a dir.

        Args:
            path (Path): The path to check.

        Returns:
            bool: True if the directory exists, False otherwise.

        Raises:
            NotADirectoryError: If the specified path exists but is not a directory.
        """
        if not path.is_dir():
            raise NotADirectoryError(f"The specified path {path} is not a dir!")
        else:
            return True

    def __check_exists(self, path):
        """
        Check if the specified directory exists.

        Args:
            path (Path): The path to check.

        Returns:
            bool: True if the directory exists, False otherwise.

        Raises:
            FileNotFoundError: If the specified path exists but is not a directory.
        """
        if not path.exists():
            raise FileNotFoundError(f"The specified path {path} does not exist!")
        else:
            return True

    @staticmethod
    @jit(nopython=True)
    def calculate_img(
        X_grid, Y_grid, x_coords, y_coords, z_coords, tunneling_current, tau, scan_h
    ):
        img = np.zeros_like(X_grid)
        for i in range(len(X_grid)):
            for j in range(len(Y_grid)):
                for a in range(len(tunneling_current)):
                    deltaR = np.linalg.norm(
                        np.array((X_grid[i, j], Y_grid[i, j], scan_h))
                        - np.array((x_coords[a], y_coords[a], z_coords[a]))
                    )
                    img[i, j] = img[i, j] - tunneling_current[a] * np.exp(-tau * deltaR)
        return img

    def get_coordinates(self) -> "tuple[list[float], list[float], list[float]]":

        x_coordinates = []
        y_coordinates = []
        z_coordinates = []
        with open(self.xyz_path, "r") as file:
            num_atoms = int(file.readline())
            file.readline()

            if self.atoms_device is not None:
                num_atoms = self.atoms_device[1]

            for _ in range(num_atoms):
                line = file.readline().split()

                x_coordinates.append(float(line[1]))
                y_coordinates.append(float(line[2]))
                z_coordinates.append(float(line[3]))
        return x_coordinates, y_coordinates, z_coordinates

    def calculate_tunneling_current(self) -> "list[float]":
        with open(self.dos_per_atom_path, "r") as f:
            data = json.load(f)

        ldos = data["LDOS"]
        tunneling_current = []
        Vmin = min(self.fermi_level, self.fermi_level + self.bias)
        Vmax = max(self.fermi_level, self.fermi_level + self.bias)

        for k, v in ldos.items():
            energy = np.array(v["energy"])
            states = np.array(v["states"])
            mask = (energy > Vmin) & (energy < Vmax)
            if np.sum(mask) < 2:
                tunneling_current.append(0.0)
            else:
                integral = np.trapz(states[mask], energy[mask])
                tunneling_current.append(integral)
        return tunneling_current

    def get_stm_img(self, image_res: tuple, tau: float, scan_h: float) -> np.ndarray:
        tunneling_current = self.calculate_tunneling_current()
        x_coords, y_coords, z_coords = self.get_coordinates()
        # Regular grid for mapping LDOS on atoms
        img_res_x = image_res[0]
        img_res_y = image_res[1]

        X = np.linspace(np.min(x_coords), np.max(x_coords), img_res_x)
        Y = np.linspace(np.min(y_coords), np.max(y_coords), img_res_y)
        X_grid, Y_grid = np.meshgrid(X, Y)
        img = self.calculate_img(
            X_grid=X_grid,
            Y_grid=Y_grid,
            x_coords=x_coords,
            y_coords=y_coords,
            z_coords=z_coords,
            tunneling_current=tunneling_current,
            tau=tau,
            scan_h=scan_h,
        )
        img = (img - np.min(img)) / (np.max(img) - np.min(img))
        img_flip = np.flipud(img)
        return img_flip

    def process_image(
        img,
        gamma=1.0,
        equalization="adaptive",
        clahe_kernel_size=(8, 8),
        clahe_clip_limit=0.01,
    ):
        img_proc = img
        img_proc = img_proc - img_proc.min()
        img_proc = img_proc / (img_proc.max() + 1e-12)

        if equalization == "global":
            img_proc = exposure.equalize_hist(img_proc)
        elif equalization == "adaptive":
            img_proc = exposure.equalize_adapthist(
                img_proc,
                kernel_size=clahe_kernel_size,
                clip_limit=clahe_clip_limit,
                nbins=256,
            )
        if gamma != 1.0:
            img_proc = np.power(img_proc, 1.0 / gamma)
        return img_proc

    @staticmethod
    def plot_image(
        img,
        cmap="hot",
        gamma=1.5,
        equalization: str = "adaptive",  # options: "none", "global", "adaptive"
        clip_eps: float = 1e-12,
        clahe_kernel_size=(16, 16),
        clahe_clip_limit=0.01,
    ):
        plt.figure(figsize=(12, 8))
        img_proc = StmSimulator._process_image(
            img,
            gamma=gamma,
            equalization=equalization,
            clip_eps=clip_eps,
            clahe_kernel_size=clahe_kernel_size,
            clahe_clip_limit=clahe_clip_limit,
        )

        im = plt.imshow(img_proc, cmap=cmap, origin="lower", vmin=0, vmax=1)
        plt.colorbar(im, fraction=0.046)
        plt.title(
            f"STM image (eq={equalization}, gamma={gamma}, ks={clahe_kernel_size}, clip={clahe_clip_limit})"
        )
        plt.axis("off")
        plt.tight_layout()
        plt.show()

    @staticmethod
    def save_png(
        img: np.ndarray,
        save_path: Path,
        colormap: int = cv2.COLORMAP_HOT,
        gamma=1.5,
        equalization: str = "adaptive",
        clahe_kernel_size=(16, 16),
        clahe_clip_limit=0.01,
    ) -> None:

        img_proc = StmSimulator.process_image(
            img,
            gamma=gamma,
            equalization=equalization,
            clahe_kernel_size=clahe_kernel_size,
            clahe_clip_limit=clahe_clip_limit,
        )
        img = (img_proc * 255).astype(np.uint8)
        img = cv2.applyColorMap(img, colormap)
        cv2.imwrite(str(save_path), img)

    @staticmethod
    def save_npy(img: np.ndarray, save_path: Path) -> None:
        np.save(str(save_path), img)


if __name__ == "__main__":
    xyz_path = Path(
        "/home/mario/Mario/Phd_code/AutoDFTB/test_batch/transport/transport_output/xyz_electrodes/graphene_2410_e.xyz"
    )
    dos_per_atom_path = Path(
        "/home/mario/Mario/Phd_code/AutoDFTB/test_batch/transport/transport_output/graphene_2410_e.json"
    )
    fermi_energy = -4.62
    bias = 0.5
    stm = StmSimulator(
        xyz_path=xyz_path,
        dos_per_atom_path=dos_per_atom_path,
        fermi_level=fermi_energy,
        bias=bias,
    )

    img = stm.get_stm_img(image_res=(256, 256), tau=5, scan_h=1)
    stm.save_png(-img, Path("test.png"))
# TODO! Integrare bene la nuova metodologia di image processing con il workflow completo
# TODO Aggiungere equalizzazione anche quando vengono salvati in np array e i png
# TODO Capire bene come gestire i nomi degli elettrodi perchè altrimenti il workflow xyz non funziona.
