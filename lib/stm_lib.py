try:
    from pathlib import Path
    import numpy as np
    import json
    from numba import jit
    import matplotlib.pyplot as plt
    import cv2

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class StmSimulator:
    def __init__(
        self, xyz_path: Path, dos_per_atom_path: Path, bias: float, fermi_level: float
    ) -> None:
        # self.__check_dir__(xyz_path)
        # self.__check_dir(dos_per_atom_path)
        self.__check_exists(xyz_path)
        self.__check_exists(dos_per_atom_path)

        self.xyz_path = xyz_path
        self.dos_per_atom_path = dos_per_atom_path
        self.bias = bias
        self.fermi_level = fermi_level

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

            for _ in range(num_atoms):
                line = file.readline().split()

                x_coordinates.append(float(line[1]))
                y_coordinates.append(float(line[2]))
                z_coordinates.append(float(line[3]))
        return x_coordinates, y_coordinates, z_coordinates

    def calculate_tunneling_current(self) -> "list[float]":
        """
        Calculate tunneling current for each atom. This module is the implementation
        of the paper Tersoff, Jerry, and Donald R. Hamann. "Theory of the scanning tunneling microscope.
        In the work the tunneling current is the integral of the LDOS with the integration interval between
        the fermi level and fermi level with a bias added.
        Returns:
            list[float]: List of tunneling currents for each atom.
        """
        with open(self.dos_per_atom_path, "r") as f:
            data = json.load(f)

        ldos = data["LDOS"]
        tunneling_current = []
        for k, v in ldos.items():
            energy, states = v["energy"], v["states"]
            energy_above_fermi = np.array(energy)
            states_above_fermi = np.array(states)
            if np.sign(self.bias) < 0:  # if energy >= fermi_energy
                condition = (self.fermi_level + self.bias < energy_above_fermi) & (
                    energy_above_fermi < self.fermi_level
                )
            else:
                condition = (self.fermi_level < energy_above_fermi) & (
                    energy_above_fermi < self.fermi_level + self.bias
                )

            energy_above_fermi = energy_above_fermi[condition]
            states_above_fermi = states_above_fermi[condition]
            integral_above_fermi = np.trapz(states_above_fermi, energy_above_fermi)
            tunneling_current.append(integral_above_fermi)
        return tunneling_current

    def get_stm_img(self, image_res: tuple, tau: float, scan_h: float) -> np.ndarray:
        tunneling_current = self.calculate_tunneling_current()
        x_coords, y_coords, z_coords = self.get_coordinates()
        # creazione griglia regolare per mappare LDOS sugli atomi
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

    @staticmethod
    def plot_image(img, cmap: str = "hot") -> None:
        plt.figure(figsize=(12, 8))
        img = (img - np.min(img)) / (np.max(img) - np.min(img))
        plt.imshow(-img, cmap=cmap)
        plt.colorbar
        plt.show()

    @staticmethod
    def save_npy(img: np.ndarray, save_path: Path) -> None:
        np.save(str(save_path), img)

    @staticmethod
    def save_png(
        img: np.ndarray, save_path: Path, colormap: int = cv2.COLORMAP_HOT
    ) -> None:
        img = (img * 255).astype(np.uint8)
        img = cv2.applyColorMap(img, colormap)
        cv2.imwrite(str(save_path), img)


if __name__ == "__main__":
    xyz_path = Path(
        "/home/tommaso/git_workspace/AutoDFTB/data/transport/xyz_files_fixed/graphene_1219_fixed.xyz"
    )
    dos_per_atom_path = Path(
        "/home/tommaso/git_workspace/AutoDFTB/data/transport/transport_output/graphene_1219_e.json"
    )
    fermi_energy = -4.62
    bias = 0.5
    stm = StmSimulator(
        xyz_path=xyz_path,
        dos_per_atom_path=dos_per_atom_path,
        fermi_level=fermi_energy,
        bias=bias,
    )

    img = stm.get_stm_img(image_res=(640, 640), tau=5, scan_h=1)
    stm.save_png(-img, Path("/home/tommaso/git_workspace/AutoDFTB/data/stm/test.png"))
