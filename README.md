<h1 align="center">
    <img src="./assets/daimon_logo.png" width="100" alt="Logo"/><br/>
  AutoDFTB 
</h1>

---

# Workflow

## Introduction
This study investigates how atomic-scale defects affect the electronic behaviour of graphene, aiming to support the design of nanoscale devices with customised properties. Building on an existing repository of defective graphene structures, a new dataset has been created using high-throughput automated workflows and Density Functional Tight Binding (DFTB) calculations. The dataset includes key electronic properties—such as electron affinity, ionisation potential, total energy, band gap, and Fermi energy—as well as simulated Scanning Tunnelling Microscopy (STM) images and quantum transport properties obtained via the Non-Equilibrium Green’s Function (NEGF) method. Fully FAIR-compliant, the dataset is designed to support multiscale workflows, enable comparison with experimental data, and foster AI-driven research in nanographene.

## Fix xyz files
Due to the fact that the original xyz files do not respect the periodicity that minimizes the flake energy, we have to add 2 "rows" of carbons to the flake. Firstly we move the major defect to the center of the flake, then we add one row to the left and one row to the right. This process is automatically carried out by `fix_xyz_dataset.py`.

## Geometry optimization

Now we have to optimize the geometry of the fixed flakes, obtained from the previous point. To do so we firstly get the standard cell, by manually optimizing the geometry and the lattice of a perfect graphene flakes with the same dimension of the flakes in the dataset.
Once the standard cell is known, we optimize the geometry with a fixed lattice for all the flakes in the dataset by running `auto_optimize_geometry.py`.

## DFTB
!!! note
    Questa è una nota speciale.


Now we can launch `auto_dftb.py` on the fixed and optimized dataset to get some target properties:
* file_name
* file_type
* n_electrons
* fermi_level_ev
* total_energy_eV
* total_energy_eV_-1
* total_energy_eV_+1
* IP_ev
* EA_ev
* band_gap_ev

## Elctrodes generator

We have to attach the electrodes and optimize the geometry of the whole structure but keeping fixed the electrodes atoms positions. TBD

## Transport

TBD

## STM

TBD