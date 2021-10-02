#!/bin/bash
export PYTHONPATH=${HOME}/Coreform-Cubit-2021.3-Lin64/bin
set -e
python build.py
python meshing/cubit_test.py --exodus ./cubit01.e --gmsh ./cubit01.gmsh --scale 1.0e-4
python meshing/add_interfaces.py --input_mesh cubit01.gmsh --output_mesh cubit01_interface.gmsh --yaml mos.yaml
python initial_refine.py  --gmsh cubit01_interface.gmsh --input_exodus cubit01.e  --output_exodus cubit01_refine.e --scale 1e4 --mincl 1e-7 --maxcl 1e-4
python refine2.py --cubit cubit01.cub5  --sizing cubit01_refine.e --output_exodus ./cubit02.e
python ../../meshing/cubit_test.py --exodus ./cubit02.e --gmsh ./cubit02.gmsh --scale 1.0e-4
python ../../meshing/add_interfaces.py --input_mesh cubit02.gmsh --output_mesh cubit02_interface.gmsh --yaml mos.yaml
python initial_refine.py  --gmsh cubit02_interface.gmsh --input_exodus cubit02.e  --output_exodus cubit02_refine.e --scale 1e4 --mincl 1e-7 --maxcl 1e-4
python refine2.py --cubit cubit01.cub5  --sizing cubit02_refine.e --output_exodus ./cubit03.e



