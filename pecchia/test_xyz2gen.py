import sys
import math


def main():
    if len(sys.argv) < 2:
        print("Usage: python xyz2gen.py filein [-s] [a b c]")
        print("filein - structure.xyz input file")
        print("-s : set supercell")
        print("a b c: orthorombic supercell lengths")
        return 1

    supercell = False
    filein = sys.argv[1]
    output_file = filein[:-4] + ".gen"

    if len(sys.argv) >= 3 and sys.argv[2] == "-s":
        supercell = True

    if supercell and len(sys.argv) == 6:
        aa = float(sys.argv[3])
        bb = float(sys.argv[4])
        cc = float(sys.argv[5])

    try:
        with open(filein, "r") as FPin:
            natm = int(FPin.readline().strip())
            FPin.readline()  # skip the second line

            atm = []
            isp = {}
            x = []
            y = []
            z = []

            for i in range(natm):
                line = FPin.readline().split()
                atm_symbol = line[0]
                atm.append(atm_symbol)
                x_coord, y_coord, z_coord = map(float, line[1:])
                x.append(x_coord)
                y.append(y_coord)
                z.append(z_coord)
                if atm_symbol not in isp:
                    isp[atm_symbol] = len(isp) + 1

        with open(output_file, "w") as output:
            if supercell:
                output.write(f" {natm} {'S'}\n")
            else:
                output.write(f" {natm} {'C'}\n")

            unique_atoms = set(atm)
            output.write(" ")
            for atom in unique_atoms:
                output.write(f" {atom}")
            output.write("\n")

            for i in range(natm):
                output.write(
                    f"{i + 1} {isp[atm[i]]} {x[i]:18.12f} {y[i]:18.12f} {z[i]:18.12f}\n"
                )

            if supercell:
                output.write("0.000000000000 0.0000000000000 0.0000000000000\n")
                output.write(f"{aa:18.12f} 0.000000000000 0.0000000000000\n")
                output.write(f"0.000000000000 {bb:18.12f} 0.0000000000000\n")
                output.write(f"0.000000000000 0.0000000000000 {cc:18.12f}\n")

    except FileNotFoundError:
        print("File error or doesn't exist")
        return 2


if __name__ == "__main__":
    sys.exit(main())
