try:
    from pathlib import Path
    from lib.utils_lib import _map_angular_momentum
    import re
    from omegaconf import open_dict

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


def extract_transport_components(file_path: Path):
    with open(str(file_path), "r") as file:
        text = file.read()

    components = {}

    # Estrai Device
    device_match = re.search(r"Device{([^{}]*({[^{}]*}[^{}]*)*)}", text, re.DOTALL)
    if device_match:
        components["device"] = device_match.group(0).strip()

    # Estrai Contact source
    source_match = re.search(
        r'Contact{([^}]*)Id\s*=\s*"source"([^}]*)}', text, re.DOTALL
    )
    if source_match:
        components["source"] = source_match.group(0).strip()

    # Estrai Contact drain
    drain_match = re.search(r'Contact{([^}]*)Id\s*=\s*"drain"([^}]*)}', text, re.DOTALL)
    if drain_match:
        components["drain"] = drain_match.group(0).strip()

    # Estrai Hamiltonian
    hamiltonian_match = re.search(r"Hamiltonian\s*=\s*DFTB{([^}]*)}", text, re.DOTALL)
    if hamiltonian_match:
        components["truncateskrange"] = hamiltonian_match.group(1).strip() + "\n}"

    return components


class DFTB:
    def __init__(self, args, file_name: Path):
        self.args = args
        self.file_name = file_name

    @property
    def geometry(self):
        if self.file_name.suffix.lower() == ".poscar":
            return (
                """
Geometry = VaspFormat {
    <<< """
                + f"'{self.file_name.name}'"
                + """ 
}\n"""
            )
        elif self.file_name.suffix.lower() == ".gen":
            return (
                """
Geometry = GenFormat {
    <<< """
                + f"'{self.file_name.name}'"
                + """ 
}\n"""
            )
        else:
            raise Exception(f"Wrong suffix for {self.file_name}")

    @property
    def driver(self):
        if not hasattr(self.args, "optimize_geometry"):
            with open_dict(self.args):
                self.args.optimize_geometry = False
        if not hasattr(self.args, "moved_atoms"):
            with open_dict(self.args):
                self.args.moved_atoms = False
        if not self.args.optimize_geometry:
            return """
Driver = {}\n"""
        else:
            if self.args.optimize_lattice:
                return (
                    """Driver = GeometryOptimization {
    Optimizer = Rational {}
    LatticeOpt = Yes
    MovedAtoms = """
                    + (
                        "1:-1"
                        if not self.args.moved_atoms
                        else f"{list(self.args.moved_atoms)[0]}:{list(self.args.moved_atoms)[1]}"
                    )
                    + """
    FixAngles = Yes
    FixLengths = No No Yes
    MaxSteps = """
                    + f"{self.args.max_steps}"
                    + """               
    OutputPrefix =  """
                    + f"opt_{self.file_name.stem}"
                    + """     
    Convergence {GradElem = 1E-4}   
    }\n"""
                )
            else:
                return (
                    """Driver = GeometryOptimization {
    Optimizer = Rational {}
    LatticeOpt = No
    MovedAtoms = """
                    + (
                        "1:-1"
                        if not self.args.moved_atoms
                        else f"{list(self.args.moved_atoms)[0]}:{list(self.args.moved_atoms)[1]}"
                    )
                    + """
    MaxSteps = """
                    + f"{self.args.max_steps}"
                    + """               
    OutputPrefix =  """
                    + f"opt_{self.file_name.stem}"
                    + """     
    Convergence {GradElem = 1E-4}   
    }\n"""
                )

    @property
    def slaterkosterfiles(self):
        return (
            """
    SlaterKosterFiles = Type2FileNames {
        Prefix = """
            + f"'{self.args.slakos}/'"
            + """
        Separator = "-"
        Suffix = ".skf"
    }\n"""
        )

    @property
    def filling(self):
        if hasattr(self.args, "fermi_temperature"):
            return (
                """
    Filling = Fermi {
        Temperature [K] = """
                + f"{self.args.fermi_temperature}"
                + """
    }\n"""
            )
        else:
            return ""

    @property
    def kpoints(self):
        return """
    KPointsAndWeights = SupercellFolding {
        1 0 0
        0 1 0
        0 0 1
        0.0 0.0 0.0
    }\n
    """

    def hamiltonian(self):
        if not hasattr(self.args, "scc") or (
            hasattr(self.args, "scc") and not self.args.scc
        ):
            scc = False
        elif hasattr(self.args, "scc") and self.args.scc:
            scc = True
        return (
            """Hamiltonian = DFTB {
    Scc = """
            + (f"Yes" if scc else "No")
            + """ """
            + f"{self.slaterkosterfiles}"
            + f"{_map_angular_momentum(self.file_name)}"
            + (f"{self.maxscciterations}" if scc else "")
            + f"{self.charge}"
            + f"{self.filling}"
            + f"{self.kpoints}"
            + f"{self.spin_polarization}"
            + f"{self.truncateskrange}"
            + f"{self.solver}"
            + """
}\n"""
        )

    @property
    def spin_polarization(self):
        if not hasattr(self.args, "spin_polarization"):
            with open_dict(self.args):
                self.args.spin_polarization = False
        if self.args.spin_polarization:
            return """
    SpinPolarization = Colinear {
        RelaxTotalSpin = Yes
    }
    SpinConstants = {
    C = {
        -0.0227
        }
    }
    """
        else:
            return ""

    @property
    def truncateskrange(self):
        try:
            if not hasattr(self, "components"):
                self.components = extract_transport_components(self.args.transport_file)
            return self.components["truncateskrange"]
        except:
            print("Warining truncateskrange block skipped!")
            return ""

    @property
    def solver(self):
        if not hasattr(self.args, "solver"):
            with open_dict(self.args):
                self.args.solver = False

        if self.args.solver == "TransportOnly":
            delta = 1e-4
            return f"Solver = TransportOnly {{\n    delta = {delta:.0e}\n}}"


        elif self.args.solver == "GreensFunction":
            return """
    Solver = GreensFunction{SaveSurfaceGFs = No}
    Electrostatics = Poisson {
        Verbosity = 101
        MinimalGrid [Angstrom] = 0.5 0.5 0.5
        SavePotential = Yes
    }
        """
        else:
            return ""

    @property
    def maxscciterations(self):
        return (
            """
    MaxSCCIterations = """
            + f"{self.args.max_iterations}"
            + """
    """
        )

    @property
    def charge(self):
        if hasattr(self.args, "charge"):
            return (
                """
        Charge = """
                + f"{self.args.charge}"
                + """
        """
            )
        else:
            return ""

    @property
    def options(self):
        return """
Options {
    WriteDetailedXml = Yes
    WriteAutotestTag = Yes
}
                """

    @property
    def analysis(self):
        if hasattr(self.args, "tunnelinganddos"):
            return (
                """
Analysis{
    TunnelingAndDOS{
    delta = 1e-4
    verbosity = """
                + f"{self.args.tunnelinganddos.verbosity}"
                + """
    EnergyRange [eV] = """
                + f"{self.args.tunnelinganddos.energy_range[0]} {self.args.tunnelinganddos.energy_range[1]}"
                + """
    EnergyStep [eV] = """
                + f"{self.args.tunnelinganddos.energy_step}"
                + """
    """
                + (
                    self.generate_region_string(
                        self.args.atoms_device[0], self.args.atoms_device[1]
                    )
                    if self.args.tunnelinganddos.compute_regions
                    else ""
                )
                + """
    }
}
                """
            )
        else:
            return """
Analysis {
    CalculateForces = Yes
    WriteEigenvectors = Yes
}
                """

    @property
    def parseroptions(self):
        return """
ParserOptions {
    ParserVersion = 6
}
                """

    def get_transport_properties(
        self, contact: str = "source", components: dict = None
    ):
        if not hasattr(self.args, "task"):
            with open_dict(self.args):
                self.args.task = False

        if components is None:

            self.components = extract_transport_components(self.args.transport_file)
            return (
                """
Transport{
    """
                + f"{self.components['device']}"
                + """
    """
                + f"{self.components['source']}"
                + """
    """
                + f"{self.components['drain']}"
                + """
    Task = ContactHamiltonian {
        contactId = """
                + f"'{contact}'"
                + """
    }
}\n        """
            )
        else:
            return (
                """
Transport{
    """
                + f"{components['device']}"
                + """
    """
                + f"{components['source']}"
                + """
    """
                + f"{components['drain']}"
                + """
    """
                + (f"{self.get_transport_task()}" if self.args.task else "")
                + """
}\n        """
            )

    def get_transport_task(self):
        if self.args.task == "UploadContacts":
            return """
    Task = UploadContacts {}
        """

    @staticmethod
    def generate_region_string(start, end):
        region_string = ""
        for i in range(start, end + 1):
            region_string += f"Region {{\n  Atoms = {i}\n}}\n"
        return region_string


def prepare_dftbplus_input(
    args,
    file_name: Path,
    out_path: Path = None,
):
    input_dftb = DFTB(args, file_name)

    if out_path is None:
        out_path = file_name.with_name("dftb_in.hsd")

    with open(str(file_name.with_name("dftb_in.hsd")), "w") as f:
        f.write(
            input_dftb.geometry
            + input_dftb.driver
            + input_dftb.hamiltonian()
            + input_dftb.options
            + input_dftb.analysis
            + input_dftb.parseroptions
        )


def prepare_contact_input(
    args, file_name: Path, out_path: Path = None, contact: str = "source"
):
    input_contact = DFTB(args, file_name)

    if out_path is None:
        out_path = file_name.with_name("dftb_in.hsd")

    with open(str(out_path), "w") as f:
        f.write(
            input_contact.geometry
            + input_contact.get_transport_properties(contact=contact)
            + input_contact.driver
            + input_contact.hamiltonian()
            + input_contact.options
            + input_contact.parseroptions
        )

    return input_contact


def prepare_transport_input(
    args, file_name: Path, components: dict, out_path: Path = None
):
    input_transport = DFTB(args, file_name)

    if out_path is None:
        out_path = file_name.with_name("dftb_in.hsd")

    with open(str(file_name.with_name("dftb_in.hsd")), "w") as f:
        f.write(
            input_transport.geometry
            + input_transport.get_transport_properties(components=components)
            + input_transport.driver
            + input_transport.hamiltonian()
            + input_transport.analysis
            + input_transport.options
            + input_transport.parseroptions
        )

    return input_transport


if __name__ == "__main__":
    pass
