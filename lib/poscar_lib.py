try:
    import os
    from pathlib import Path

except Exception as e:
    print(f"Some module are missing from {__file__}: {e}\n")


# Get box size from xyz file or use the default box size parameter
def get_box_info(input_file_name, default_box_size):
    with open(input_file_name) as f:
        load_lines = f.readlines()
        try:
            box_size_parameter = (((load_lines[1].split("["))[1].split("]"))[0]).split(
                ","
            )
            box_size_parameter = list(map(float, box_size_parameter))

        # If box info is not correct, use default box parameters
        except:
            box_size_parameter = default_box_size

        # If box info is missing, use default box parameters
        if not len(box_size_parameter) == 9:
            box_size_parameter = default_box_size

    return box_size_parameter


# Extract molecule structure from xyz file
def get_molecule_structure(input_file_name):
    molecule_structure = []
    with open(input_file_name) as f:
        load_lines = f.readlines()
        for i in range(2, int(load_lines[0]) + 2):
            line = load_lines[i][:-1].split(" ")
            no_space_line = []

            # Remove space and tab from list
            for object in line:
                if not len(object) == 0:
                    no_space_line.append(object)

            molecule_structure.append(
                [
                    no_space_line[0],
                    float(no_space_line[1]),
                    float(no_space_line[2]),
                    float(no_space_line[3]),
                ]
            )

    # Re-rank all atoms base on the elements
    molecule_structure.sort(key=lambda x: x[0])

    return molecule_structure


# Calculate the molecule's center (average position of all atoms) and move it to the center of box
def recenter_molcecule(molecule_structure, box_size_parameter):
    recenter_molecule_structure = []
    molceule_x = 0
    molceule_y = 0
    molceule_z = 0

    # Calculate molecule's center by average position of all atoms
    for ele in molecule_structure:
        molceule_x += ele[1]
        molceule_y += ele[2]
        molceule_z += ele[3]
    molecule_number = len(molecule_structure)
    molecule_center = [
        molceule_x / molecule_number,
        molceule_y / molecule_number,
        molceule_z / molecule_number,
    ]

    # Calculate box's center
    box_center = [
        box_size_parameter[0] / 2,
        box_size_parameter[4] / 2,
        box_size_parameter[8] / 2,
    ]

    # Calculate shift value and apply to all atoms
    x_shift = molecule_center[0] - box_center[0]
    y_shift = molecule_center[1] - box_center[1]
    z_shift = molecule_center[2] - box_center[2]
    for ele in molecule_structure:
        recenter_molecule_structure.append(
            [ele[0], ele[1] - x_shift, ele[2] - y_shift, ele[3] - z_shift]
        )

    return recenter_molecule_structure


# Find elements type and each type's number
def get_elements_and_number(molecule_structure):
    ele_list = []
    ele_non_repeat_list = []
    ele_number = []
    for atom in molecule_structure:
        ele_list.append(atom[0])

    # Remove repeated elements without change their rank
    ele_non_repeat_list = list({}.fromkeys(ele_list).keys())

    for ele in ele_non_repeat_list:
        ele_number.append(ele_list.count(ele))

    return [ele_non_repeat_list, ele_number]


# Write the info into POSCAR file
def write_POSCAR(
    input_file_name,
    box_size_parameter,
    recenter_molcecule_structure,
    elements_and_number,
    out_file: Path,
):
    with open(str(out_file), "w") as f:
        f.write("Input file generated from " + input_file_name + "\n")
        f.write("1.0\n")
        f.write(
            " "
            + str(box_size_parameter[0])
            + " "
            + str(box_size_parameter[1])
            + " "
            + str(box_size_parameter[2])
            + "\n"
        )
        f.write(
            " "
            + str(box_size_parameter[3])
            + " "
            + str(box_size_parameter[4])
            + " "
            + str(box_size_parameter[5])
            + "\n"
        )
        f.write(
            " "
            + str(box_size_parameter[6])
            + " "
            + str(box_size_parameter[7])
            + " "
            + str(box_size_parameter[8])
            + "\n"
        )
        for ele in elements_and_number[0]:
            f.write(" " + ele)
        f.write("\n")
        for ele_num in elements_and_number[1]:
            f.write(" " + str(ele_num))
        f.write("\n")
        f.write("Cartesian\n")
        for atom in recenter_molcecule_structure:
            f.write(
                "  " + str(atom[1]) + "  " + str(atom[2]) + "  " + str(atom[3]) + "\n"
            )


def xyz_to_poscar(
    xyz_file: Path,
    poscar_file: Path,
    default_box_size: list = [100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0, 100.0],
):

    molecule_structure = get_molecule_structure(str(xyz_file))

    box_size_parameter = get_box_info(str(xyz_file), default_box_size)

    recenter_molcecule_structure = recenter_molcecule(
        molecule_structure, box_size_parameter
    )

    elements_and_number = get_elements_and_number(recenter_molcecule_structure)
    # Write all info into POSCAR file
    write_POSCAR(
        str(xyz_file),
        box_size_parameter,
        recenter_molcecule_structure,
        elements_and_number,
        poscar_file,
    )


if __name__ == "__main__":
    pass
