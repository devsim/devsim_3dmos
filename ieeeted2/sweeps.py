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
#parser.add_argument(
#    '--',         help='the exodus file for output', required=True)
args = parser.parse_args()

#ds.set_parameter(name="debug_level", value="verbose")

#ds.set_parameter(name="threads_available", value=8)
if False:
    ds.set_parameter(name = "extended_solver", value=True)
    ds.set_parameter(name = "extended_model", value=True)
    ds.set_parameter(name = "extended_equation", value=True)

# TODO: write out mesh, and then read back in as separate test
device = mos90.device

mos_create.create(device, args.gmsh, None)

mos90.create_potential()

ds.solve(type="dc", absolute_error=1.0e-13, relative_error=1e-12, maximum_iterations=30)

# bulk mobility
mos90.setup_low_field_dd()

for r in mos90.silicon_regions:
    ds.set_parameter(device=device, region=r, name="jemin", value=0)
    ds.set_parameter(device=device, region=r, name="jhmin", value=0)


mos90.setup_eeb_dd(model=args.model, hfs=args.hfs)


#write_devices(file="debug.msh", type="devsim")
ds.solve(type="dc", absolute_error=1.0e30, relative_error=1e-8, maximum_iterations=100)
#ds.write_devices(file="gmsh_mos2d_dd_kla_zero.dat", type="tecplot")
#ds.write_devices(file="gmsh_mos2d_dd_kla_zero", type="vtk")


#drainbias=ds.get_parameter(device=device, name=GetContactBiasName("drain"))
#gatebias=ds.get_parameter(device=device, name=GetContactBiasName("gate"))




printer = mos90.create_csv_printer(args.csv)


mos90.printAllCurrents(device)

ds.solve(type="dc", absolute_error=1.0e30, relative_error=1e-8, maximum_iterations=100)
mos90.printAllCurrents(device)


vgrange = (-0.1, 1.0, 12)
vdrange = (0.1, 0.2, 2)
#vdrange = (0.1, 2.0, 20)

gatebias=ds.get_parameter(device=device, name=GetContactBiasName("gate"))
drainbias=ds.get_parameter(device=device, name=GetContactBiasName("drain"))
vgstart = vgrange[0]
vgstep  = (vgstart-gatebias)/4.
vdstart = vdrange[0]

rampbias(device, "gate", vgstart, vgstep, 0.001, 25, 1e-8, 1e30, mos90.printAllCurrents)

vgstep  = (vgrange[1]-vgrange[0])/(vgrange[2] - 1)/4.
vgmax = vgrange[1]

backup = None

for vd in np.linspace(*vdrange):
    vd = float(vd)
    if backup:
        mos90.restore_backup(backup)
        ds.solve(type="dc", absolute_error=1.0e30, relative_error=1e-4, maximum_iterations=100)
        backup = None

    gatebias = ds.get_parameter(device=device, name=GetContactBiasName("gate"))
    if gatebias != vgstart:
        raise RuntimeError("Unexpected backup gate bias %g != %g" % (gatebias, vgstart))

    drainbias=ds.get_parameter(device=device, name=GetContactBiasName("drain"))
    vdstep = (vd - drainbias)/4.
    rampbias(device, "drain", vd, vdstep, 0.01, 25, 1e-4, 1e30, mos90.printAllCurrents)

    # this is the intial drain bias for the next run
    backup = mos90.save_backup()

    #write to csv the intial bias point
    printer(device)
    try:
        rampbias(device, "gate", vgmax, vgstep, 0.01, 25, 1e-4, 1e30, printer)
    except Exception as e:
        print('Caught runtime exception during gate sweep, going to next bias point') 
        print(str(e))

#backup = get_backup()
#mos90.restore_backup(backup)
#ds.solve(type="dc", absolute_error=1.0e30, relative_error=1e-8, maximum_iterations=100)





#rampbias(device, "drain", 0.5, 0.1, 0.001, 50, 1e-6, 1e30, mos90.printAllCurrents)

#ds.write_devices(file="gmsh_mos2d_dd_kla.dat", type="tecplot")
#ds.write_devices(file="gmsh_mos2d_dd_kla", type="vtk")

