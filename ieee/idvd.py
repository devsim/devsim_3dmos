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

#set_parameter -name threads_available -value 1
#set_parameter -name threads_task_size -value 1024

import devsim as ds
from newmodels.simple_physics import *
from newmodels.ramp import *
from newmodels.Klaassen import *
from newmodels.mos_physics import *
import mos_create
import mos90
import numpy as np
import argparse

#ds.set_parameter(name="debug_level", value="verbose")

ds.set_parameter(name="threads_available", value=8)
if False:
    ds.set_parameter(name = "extended_solver", value=True)
    ds.set_parameter(name = "extended_model", value=True)
    ds.set_parameter(name = "extended_equation", value=True)

parser = argparse.ArgumentParser(description='perform sweeps')
parser.add_argument(
    '--gmsh',        help='the gmsh file for input', required=True)
parser.add_argument(
    '--csv',         help='name of output csv', required=True)
parser.add_argument(
    '--model',       help='name of the simulation model selection', required=True)
hfs_parser = parser.add_mutually_exclusive_group(required=True)
hfs_parser.add_argument('--hfs', dest='hfs', action='store_true')
hfs_parser.add_argument('--no-hfs', dest='hfs', action='store_false')
parser.set_defaults(feature=True)
args = parser.parse_args()

vgmax = 1.0
vdmax = 1.0
hfstype=args.hfs
modelname=args.model
csvname = args.csv


# TODO: write out mesh, and then read back in as separate test
device = mos90.device

mos_create.create(device, "cubit02_interface.gmsh", "foo.msh")

mos90.create_potential()

ds.solve(type="dc", absolute_error=1.0e-13, relative_error=1e-12, maximum_iterations=30)

# bulk mobility
mos90.setup_low_field_dd()

for r in mos90.silicon_regions:
    ds.set_parameter(device=device, region=r, name="jemin", value=0)
    ds.set_parameter(device=device, region=r, name="jhmin", value=0)

#ds.symdiff(expr="define(nodiff(x), 1.0)")
#ds.register_function(name="nodiff", nargs=1, procedure=lambda myarg: myarg)

mos90.setup_eeb_dd(model=modelname, hfs=hfstype)


#write_devices(file="debug.msh", type="devsim")
ds.solve(type="dc", absolute_error=1.0e30, relative_error=1e-8, maximum_iterations=100)
#ds.write_devices(file="gmsh_mos2d_dd_kla_zero.dat", type="tecplot")
#ds.write_devices(file="gmsh_mos2d_dd_kla_zero", type="vtk")


#drainbias=ds.get_parameter(device=device, name=GetContactBiasName("drain"))
#gatebias=ds.get_parameter(device=device, name=GetContactBiasName("gate"))

#mos90.printAllCurrents(device)

#ds.set_parameter(device=device, name=GetContactBiasName("drain"), value=0.001)
#ds.solve(type="dc", absolute_error=1.0e30, relative_error=1e-8, maximum_iterations=100)

mos90.printAllCurrents(device)


printer = mos90.create_csv_printer(csvname)

rampbias(device, "gate",  vgmax, 0.025, 0.01, 10, 1e-5, 1e30, mos90.printAllCurrents)
printer(device)
rampbias(device, "drain", vdmax, 0.025, 0.001, 25, 1e-5, 1e30, printer)

##CreateElementModel(device, "bulk", "mu_r0", "mu_vsat_e/mu_bulk_e")
##CreateElementModel(device, "bulk", "mu_r1", "mu_e_0/mu_bulk_e")
##CreateElementModel(device, "bulk", "mu_r2", "mu_vsat_e/mu_e_0")
##
##gate_node=ds.get_element_node_list(device=device, region="oxide", contact="gate")[0][0]
##gate_potential = ds.get_node_model_values(device=device, region="oxide", name="Potential")[gate_node]
##ds.set_node_value(device=device, region="gate", name="Potential", value=gate_potential)
##
##ds.write_devices(file="mu_ratio.tec", type="tecplot")
###ds.write_devices(file="gmsh_mos2d_dd_kla", type="vtk")

