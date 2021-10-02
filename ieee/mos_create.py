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

from devsim import *
import pandas
import scipy.interpolate

def create(device, infile, outfile=None):
    #TODO: POLY GATE WORKFUNCTION
    #TODO: POLY GATE entire contact

    create_gmsh_mesh(file=infile, mesh="mos2d")
    add_gmsh_region    (mesh="mos2d", gmsh_name="bulk",    region="bulk", material="Silicon")
    add_gmsh_region    (mesh="mos2d", gmsh_name="oxide",    region="oxide", material="Oxide")
    add_gmsh_region    (mesh="mos2d", gmsh_name="gate",    region="gate", material="Silicon")
    add_gmsh_region    (mesh="mos2d", gmsh_name="nitride0",    region="nitride0", material="Oxide")
    add_gmsh_region    (mesh="mos2d", gmsh_name="nitride1",    region="nitride1", material="Oxide")
    add_gmsh_contact   (mesh="mos2d", gmsh_name="drain_contact",  region="bulk", name="drain", material="metal")
    add_gmsh_contact   (mesh="mos2d", gmsh_name="drain_contact",  region="oxide", name="drain_ox", material="metal")
    add_gmsh_contact   (mesh="mos2d", gmsh_name="source_contact", region="bulk", name="source", material="metal")
    add_gmsh_contact   (mesh="mos2d", gmsh_name="source_contact", region="oxide", name="source_ox", material="metal")
    add_gmsh_contact   (mesh="mos2d", gmsh_name="body_contact",   region="bulk", name="body", material="metal")
    add_gmsh_contact   (mesh="mos2d", gmsh_name="gate_contact",   region="oxide", name="gate", material="metal")
#    add_gmsh_interface (mesh="mos2d", gmsh_name="gate_oxide_interface", region0="gate", region1="oxide", name="gate_oxide")
    add_gmsh_interface (mesh="mos2d", gmsh_name="bulk_oxide_interface", region0="bulk", region1="oxide", name="bulk_oxide")
    add_gmsh_interface (mesh="mos2d", gmsh_name="nitride0_oxide_interface", region0="nitride0", region1="oxide", name="nitride0_oxide")
    add_gmsh_interface (mesh="mos2d", gmsh_name="nitride1_oxide_interface", region0="nitride1", region1="oxide", name="nitride1_oxide")
    finalize_mesh(mesh="mos2d")
    create_device(mesh="mos2d", device=device)

    #### all variable substitutions are immediate, since they are locked into the mesh
    xpos = get_node_model_values(device=device, region="bulk", name = "x")
    ypos = get_node_model_values(device=device, region="bulk", name = "y")

    source_doping = pandas.read_table('doping/source.doping', sep="\s+", names=['x', 'y', 'v'])
    drain_doping = pandas.read_table('doping/drain.doping', sep="\s+", names=['x', 'y', 'v'])
    ssr_doping = pandas.read_table('doping/ssr.doping', sep="\s+", names=['y', 'v'])

    # x and y would be in micron
    ssr = scipy.interpolate.interp1d(ssr_doping['y']*1e-4, ssr_doping['v'], "linear", fill_value=0.0)
    drain = scipy.interpolate.LinearNDInterpolator(list(zip(drain_doping['x']*1e-4, drain_doping['y']*1e-4)), drain_doping['v'], fill_value=0.0)
    source = scipy.interpolate.LinearNDInterpolator(list(zip(source_doping['x']*1e-4, source_doping['y']*1e-4)), source_doping['v'], fill_value=0.0)

    acceptor = [0.0]*len(xpos)
    donor    = [0.0]*len(xpos)
    net_doping = [0.0]*len(xpos)
    for i in range(len(xpos)):
        xl = xpos[i]
        yl = ypos[i]
        a = 0.0
        d = 0.0
        if yl < 0.0:
            yl = 0.0
        acceptor[i] += float(ssr(yl))

        val = 0.0
        if xl < 0.0:
            val = float(source(xl,yl))
        else:
            val = float(drain(xl,yl))
        # n type is net donor
        if val < 0.0:
            acceptor[i] -= val
        else:
            donor[i] += val
    node_solution(device=device, region="bulk", name="Acceptors")
    set_node_values(device=device, region="bulk", name="Acceptors", values=acceptor)
    node_solution(device=device, region="bulk", name="Donors")
    set_node_values(device=device, region="bulk", name="Donors", values=donor)
    node_model(device=device, region="bulk", name="NetDoping", equation="Donors-Acceptors")
    node_model(device=device, region="bulk", name="AbsDoping", equation="abs(NetDoping)")
    node_model(device=device, region="bulk", name="logDoping", equation="log(AbsDoping)/log(10)")

    if outfile:
        if outfile == infile:
            raise RuntimeError("outfile and infile cannot match")
        write_devices(file=outfile)

if __name__ == "__main__":
    create("test", "cubit01_interface.gmsh", "debug.msh")
    write_devices(file="debug.tec", type="tecplot")

