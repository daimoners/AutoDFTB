try:
    from pathlib import Path

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


class SetupGeom:
    def __init__(self, args, file_name: Path):
        self.args = args
        self.file_name = file_name

    @property
    def geometry(self):
        return (
            """Geometry = GenFormat {
    <<< """
            + f"'{self.file_name.name}'"
            + """ 
}\n"""
        )

    @property
    def transport(self):
        return (
            """Transport {
    """
            + f"{self.contact('source')}"
            + """
    """
            + f"{self.contact('drain')}"
            + """
    """
            + f"{self.task()}"
            + """
}"""
        )

    def contact(self, id: str = "source"):
        return (
            """Contact {
        Id = """
            + f"'{id}'"
            + """
        Atoms = {"""
            + (
                f"{self.args.atoms_source[0]}:{self.args.atoms_source[1]}"
                if id == "source"
                else f"{self.args.atoms_drain[0]}:{self.args.atoms_drain[1]}"
            )
            + """}
        ContactVector [Angstrom] = """
            + f"{self.args.contact_vector[0]} {self.args.contact_vector[1]} {self.args.contact_vector[2]}"
            + """
        PLsDefined = """
            + f"{self.args.plsdefined}"
            + """
    }"""
        )

    def task(self, cutoff: float = 5.0):
        return (
            """Task = SetupGeometry{
        TruncateSKRange{
            SKMaxDistance [AA] = """
            + f"{cutoff}"
            + """
            HardCutOff = Yes
        }
    }"""
        )


def prepare_setupgeom_input(args, file_name: Path, out_path: Path = None):
    input_setupgeom = SetupGeom(args, file_name)

    if out_path is None:
        out_path = file_name.with_name("setup_in.hsd")

    with open(str(file_name.with_name("setup_in.hsd")), "w") as f:
        f.write(input_setupgeom.geometry + input_setupgeom.transport)

    return input_setupgeom


if __name__ == "__main__":
    pass
