import cubit
import argparse

parser = argparse.ArgumentParser(description='Convert between Cubit and Gmsh format')
parser.add_argument(
    '--cubit',           help='the cubit file to operate on', required=True)
parser.add_argument(
    '--sizing',         help='the exodus file for sizing', required=True)
parser.add_argument(
    '--output_exodus',         help='the exodus file for output', required=True)
args = parser.parse_args()

#The interior points line is critical
cubit.init([])

cubit.cmd('''
open "%(cubit)s"
volume all scheme tetmesh
volume all tetmesh growth_factor 2
set tetmesher optimize overconstrained tetrahedra on
set tetmesher optimize overconstrained edges on
set tetmesher optimize sliver on
set tetmesher optimize level 5
set tetmesher boundary recovery off
set tetmesher interior points on

import sizing function "%(sizing)s" block all variable "rdata" time 0
volume 1 sizing function type exodus
mesh volume all
set exodus netcdf4 on
export mesh "%(output_exodus)s"  overwrite
''' % {
  'cubit' : args.cubit,
  'sizing' : args.sizing,
  'output_exodus' : args.output_exodus,
})
#volume 1 3 4 5 sizing function type exodus

