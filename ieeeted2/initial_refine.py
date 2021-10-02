# Copyright 2021 Devsim LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import shutil
import timedata
import math
import mos_create
import devsim
import numpy as np
from newmodels.simple_physics import *
from newmodels.ramp import *
from meshing import background_mesh
import mos90

if False:
    devsim.set_parameter(name = "extended_solver", value=True)
    devsim.set_parameter(name = "extended_model", value=True)
    devsim.set_parameter(name = "extended_equation", value=True)

import argparse
parser = argparse.ArgumentParser(description='Convert between Cubit and Gmsh format')
parser.add_argument(
    '--gmsh',           help='the gmsh file for input', required=True)
parser.add_argument(
    '--input_exodus',         help='the exodus file for input', required=True)
parser.add_argument(
    '--output_exodus',         help='the exodus file for output', required=True)
parser.add_argument(
    '--scale',         help='scale to apply', type=float, required=True)
parser.add_argument(
    '--mincl',         help='minimum characteristic length', type=float, required=True)
parser.add_argument(
    '--maxcl',         help='maximum characteristic length', type=float, default=1e8)
args = parser.parse_args()

mincl = float(args.mincl)
maxcl = float(args.maxcl)
scale = float(args.scale)

device = mos90.device

mos_create.create(device=device, infile=args.gmsh, outfile="test.msh")
devsim.write_devices(file="test.tec", type="tecplot")

mos90.create_potential()

ds.solve(type="dc", absolute_error=1.0e-13, relative_error=1e-10, maximum_iterations=30)

mos90.setup_simple_dd()

ds.solve(type="dc", absolute_error=1.0e30, relative_error=1e-5, maximum_iterations=30)

collectrefinements, refinement_dict = mos90.setup_refinement_collection()

#TODO: use more increments for collection
collectrefinements(device)


rampbias(device, "gate",  1.0, 0.5, 0.001, 25, 1e-5, 1e30, collectrefinements)
rampbias(device, "drain", 2.5, 0.1, 0.001, 25, 1e-5, 1e30, collectrefinements)

node_refinements = mos90.get_node_refinements(refinement_dict, mincl, maxcl)

data = mos90.get_coordinate_refinements(node_refinements, maxcl, scale)

print(data)
print(min(data))
print(max(data))
devsim.write_devices(file="test2.tec", type="tecplot")

shutil.copyfile(args.input_exodus, args.output_exodus)
timedata.add_variable(args.output_exodus, 'rdata', data)

