try:
    from pathlib import Path
    from lib.utils_lib import _map_angular_momentum
    import re

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


# class DFTB:
#     def __init__(self, args, file_name: Path):
#         self.args = args
#         self.file_name = file_name

#     @property
#     def geometry(self):
#         return (
#             """Geometry = VaspFormat {
#     <<< """
#             + f"'{self.file_name.name}'"
#             + """
#     }\n"""
#         )

#     @property
#     def driver(self):
#         if not self.args.optimize_geometry:
#             return """Driver = {}\n"""
#         else:
#             return (
#                 """Driver = GeometryOptimization {
#     Optimizer = Rational {}
#     LatticeOpt = Yes
#     FixAngles = Yes
#     FixLengths = No No Yes
#     MaxSteps = """
#                 + f"{self.args.max_steps}"
#                 + """
#     OutputPrefix =  """
#                 + f"opt_{self.file_name.name}"
#                 + """
#     Convergence {GradElem = 1E-3}
#     }\n"""
#             )

#     @property
#     def slaterkosterfiles(self):
#         return (
#             """
#     SlaterKosterFiles = Type2FileNames {
#         Prefix = """
#             + f"'{self.args.slakos}/'"
#             + """
#         Separator = "-"
#         Suffix = ".skf"
#     }\n"""
#         )

#     @property
#     def filling(self):
#         return (
#             """
#     Filling = Fermi {
#         Temperature [K] = """
#             + f"{self.args.fermi_temperature}"
#             + """
#     }\n"""
#         )

#     @property
#     def kpoints(self):
#         return """
#     KPointsAndWeights = SupercellFolding {
#         1 0 0
#         0 1 0
#         0 0 1
#         0.5 0.5 0.0
#     }\n
#     """

#     @property
#     def hamiltonian(self):
#         return (
#             """Hamiltonian = DFTB {
#     Scc = Yes """
#             + f"{self.slaterkosterfiles}"
#             + f"{_map_angular_momentum(self.file_name)}"
#             + """
#     MaxSCCIterations = """
#             + f"{self.args.max_iterations}"
#             + """
#     Charge = """
#             + f"{self.args.charge}\n"
#             + f"{self.filling}"
#             + f"{self.kpoints}"
#             + """
# }\n"""
#         )

#     @property
#     def options(self):
#         return """
# Options {
#     WriteDetailedXml = Yes
# }
#                 """

#     @property
#     def analysis(self):
#         return """
# Analysis {
#     CalculateForces = Yes
#     WriteEigenvectors = Yes
# }
#                 """

#     @property
#     def parseroptions(self):
#         return """
# ParserOptions {
#     ParserVersion = 12
# }
#                 """


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
            return """
Driver = {}\n"""
        if not self.args.optimize_geometry:
            return """
Driver = {}\n"""
        else:
            return (
                """Driver = GeometryOptimization {
    Optimizer = Rational {}
    LatticeOpt = Yes
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
            + f"{self.truncateskrange}"
            + f"{self.solver}"
            + """
}\n"""
        )

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
        if hasattr(self.args, "solver"):
            return (
                """
    Solver = """
                + f"{self.args.solver}"
                + """{}
        """
            )
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
    verbosity = """
                + f"{self.args.tunnelinganddos.verbosity}"
                + """
    EnergyRange [eV] = """
                + f"{self.args.tunnelinganddos.energy_range[0]} {self.args.tunnelinganddos.energy_range[1]}"
                + """
    EnergyStep [eV] = """
                + f"{self.args.tunnelinganddos.energy_step}"
                + """
    computeLDOS = """
                + f"{self.args.tunnelinganddos.compute_ldos}"
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
}\n        """
            )


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
