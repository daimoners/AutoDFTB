#!/bin/bash
set -e  # Exit if any command fails

start_total=$(date +%s)

echo "==============================="
echo "Starting fix_xyz"
echo "==============================="
start1=$(date +%s)
python fix_xyz_dataset.py
end1=$(date +%s)
echo "Finished fixing xyz in $((end1 - start1)) seconds."

echo "==============================="
echo "Starting geometry optimization"
echo "==============================="
start2=$(date +%s)
python auto_optimize_geometry.py
end2=$(date +%s)
echo "Finished geometry optimization in $((end2 - start2)) seconds."

echo "==============================="
echo "Starting dftb simulations"
echo "==============================="
start3=$(date +%s)
python3 auto_dftb.py
end3=$(date +%s)
echo "Finished dftb script in $((end3 - start3)) seconds."

echo "==============================="
echo "Starting electrodes simulations"
echo "==============================="
start4=$(date +%s)
python3 electrodes_generator.py
end4=$(date +%s)
echo "Finished electrodes generation script in $((end3 - start3)) seconds."

echo "==============================="
echo "Starting transport simulations"
echo "==============================="
start5=$(date +%s)
python3 auto_transport.py
end5=$(date +%s)
echo "Finished transport script in $((end3 - start3)) seconds."

echo "==============================="
echo "Starting stm simulations"
echo "==============================="
start6=$(date +%s)
python3 auto_stm.py
end6=$(date +%s)
echo "Finished transport script in $((end3 - start3)) seconds."

end_total=$(date +%s)
echo "==============================="
echo "All scripts completed successfully!"
echo "Total time: $((end_total - start_total)) seconds."
echo "==============================="
