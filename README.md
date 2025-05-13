<h1 align="center">
    <img src="./assets/daimon_logo.png" width="100" alt="Logo"/><br/>
  AutoDFTB 
</h1>

---

# Workflow

## Introduction
This study investigates how atomic-scale defects affect the electronic behaviour of graphene, aiming to support the design of nanoscale devices with customised properties. Building on an existing repository of defective graphene structures, a new dataset has been created using high-throughput automated workflows and Density Functional Tight Binding (DFTB) calculations using DFTB+. The dataset includes key electronic properties—such as electron affinity, ionisation potential, total energy, band gap, and Fermi energy—as well as simulated Scanning Tunnelling Microscopy (STM) images and quantum transport properties obtained via the Non-Equilibrium Green’s Function (NEGF) method. Fully FAIR-compliant, the dataset is designed to support multiscale workflows, enable comparison with experimental data, and foster AI-driven research in nanographene.

The dataset generation workflow is outlined in Fig. 1a. Atomic coordinates of graphene samples were sourced from a dataset comprising 562,217 periodic structures, each in XYZ format and containing 206 to 447 atoms. These structures share a common 2D periodicity, and their total electronic energies were computed at the DFT level using VASP.

![alt text](assets/workflow.png)
Figure 1.: a) HDF5 dataset generation workflow, b) Distribution of the number of atoms of the reference dataset with respect to the complete initial dataset, c) Fix procedure of the original DG structures

## STEP 0: Setup environment (Suggested)
* Install miniconda
* create env with `conda create -n <env_name> python==3.10.13`
* Install the requirements `pip install  -r requirements.txt`
* Download the binary precompiled of dftb+ from `https://github.com/dftbplus/dftbplus/releases`
Ecco una versione corretta e più chiara della nota in inglese britannico:


> **NOTE:** Each step has its own configuration file to ensure modularity. When launching a specific step, remember to update the `package_path` in the corresponding config file.
For example, **Step 1** runs a Python script called `fix_xyz_dataset.py`, which uses the associated configuration file `config/fix_xyz_dataset.yml`.


## STEP 1: Fix xyz files
To ensure relevance to experimental conditions, structures with an in-plane carbon atom density of at least ~78% of pristine graphene were selected. From these, 50,000 structures were chosen for the reference dataset (see Fig. 1b). To minimise edge effects in transport simulations, the largest defect in each flake was centred, and the flake was repositioned so that the atom with the lowest x and y coordinates was at (0, 0).

As the original dataset's structures lacked the periodicity necessary to preserve graphene's aromaticity, two additional rows of carbon atoms in an armchair configuration were appended at both ends. This modification reinstates graphene’s intrinsic periodicity, which is crucial for maintaining its electronic properties—particularly in partially periodic systems used in device-level transport calculation.
This process is automatically carried out by `fix_xyz_dataset.py`.

`python fix_xyz_dataset.py`

> **NOTE:** This process works without DFTB+ and only requires the installation of the packages listed in the `requirements.txt`.

## STEP 2: Geometry optimization
Now we have to optimize the geometry of the fixed flakes, obtained from the previous point. To do so we firstly get the standard cell, by manually optimizing the geometry and the lattice of a perfect graphene flakes with the same dimension of the flakes in the dataset.
Once the standard cell is known, we optimize the geometry with a fixed lattice for all the flakes in the dataset by running `auto_optimize_geometry.py`.

>**NOTE:** This workflow, starting from the geometry optimisation step, is designed to be run with SLURM, which is the typical way to manage multiple jobs on a cluster. If you wish to run it locally, simply change the scheduler option in all the files within the `config` folder, selecting one of the available options: `[local, slurm]`.

## STEP3: DFTB Simulations
All electronic properties calculations were performed with the DFTB+ package Prior to electronic property calculations, geometry optimizations were performed to ensure stable configurations of the DG flakes. This step was crucial to minimize the total energy and remove any spurious forces acting on the atoms.

Now we can launch `auto_dftb.py` on the fixed and optimized dataset to get some target properties, in the output we have a `flake_name_NUM.json` file with the properties below:

| Property Name           | Unit              |
|-------------------------|-------------------|
| `file_name`             | —                 |
| `file_type`             | —                 |
| `n_electrons`           | — (count)         |
| `fermi_level_ev`        | eV                |
| `total_energy_eV`       | eV                |
| `total_energy_eV_-1`    | eV                |
| `total_energy_eV_+1`    | eV                |
| `IP_ev`                 | eV                |
| `EA_ev`                 | eV                |
| `band_gap_ev`           | eV                |

JSON file example:
```json
{
    "n_electrons": 714.0,
    "fermi_level_ev": -5.2408,
    "total_energy_eV": -17434.2747,
    "file_name": "graphene_1131_opt",
    "file_type": "POSCAR",
    "total_energy_eV_-1": -17439.4289,
    "total_energy_eV_+1": -17428.9339,
    "IP_ev": 5.154199999997218,
    "EA_ev": -5.340800000001764,
    "band_gap_ev": -10.494999999998981
}
```
## Elctrodes generator

We have to attach the electrodes and optimize the geometry of the whole structure but keeping fixed the electrodes atoms positions. TBD

## Transport

TBD

## STM

TBD

## HD5
TBD