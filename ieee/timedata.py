import netCDF4
import numpy as np

# TODO: error out if variable is there or size mismatch
def add_variable(ifile, name, data):
    ncfile = netCDF4.Dataset(ifile, 'a')

    num_nodes = ncfile.dimensions['num_nodes'].size
    mydata = ncfile.createVariable('vals_nod_var1', np.float64, ('time_step', 'num_nodes'))
    #data = ncfile.variables['coordx'][:]
    mydata[0,:] = data
    ncfile.variables['time_whole'][:] = 0
    ncfile.createDimension('num_nod_var', 1)
    name_nod_var = ncfile.createVariable('name_nod_var', 'S1', ('num_nod_var', 'len_name'))
    len_name = ncfile.dimensions['len_name'].size
    name_nod_var[0] = netCDF4.stringtoarr(name, len_name)
    ncfile.close()

