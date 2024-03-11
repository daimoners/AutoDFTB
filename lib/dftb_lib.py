try:
    from pathlib import Path
    from lib.utils_lib import _map_angular_momentum

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class DFTB:
    def __init__(self, args, file_name: Path):
        self.args = args
        self.file_name = file_name

    @property
    def geometry(self):
        return (
            """Geometry = VaspFormat {
    <<< """
            + f"'{self.file_name.name}'"
            + """ 
    }\n"""
        )

    @property
    def driver(self):
        if not self.args.optimize_geometry:
            return """Driver = {}\n"""
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
                + f"opt_{self.file_name.name}"
                + """     
    Convergence {GradElem = 1E-3}   
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
        return (
            """
    Filling = Fermi {
        Temperature [K] = """
            + f"{self.args.fermi_temperature}"
            + """
    }\n"""
        )

    @property
    def kpoints(self):
        return """
    KPointsAndWeights = SupercellFolding {
        1 0 0
        0 1 0
        0 0 1
        0.5 0.5 0.0
    }\n
    """

    @property
    def hamiltonian(self):
        return (
            """Hamiltonian = DFTB {
    Scc = Yes """
            + f"{self.slaterkosterfiles}"
            + f"{_map_angular_momentum(self.file_name)}"
            + """
    MaxSCCIterations = """
            + f"{self.args.max_iterations}"
            + """ 
    Charge = """
            + f"{self.args.charge}\n"
            + f"{self.filling}"
            + f"{self.kpoints}"
            + """
}\n"""
        )

    @property
    def options(self):
        return """
Options {
    WriteDetailedXml = Yes
}
                """

    @property
    def analysis(self):
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
    ParserVersion = 12
}
                """


def prepare_dftbplus_input(
    args,
    file_name: Path,
):
    input_dftb = DFTB(args, file_name)

    with open(str(file_name.with_name("dftb_in.hsd")), "w") as f:
        f.write(
            input_dftb.geometry
            + input_dftb.driver
            + input_dftb.hamiltonian
            + input_dftb.options
            + input_dftb.analysis
            + input_dftb.parseroptions
        )


if __name__ == "__main__":
    pass
