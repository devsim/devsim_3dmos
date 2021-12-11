
import pandas
import matplotlib.pyplot as plt

files = ('bulk_id_vg.txt', 'bulk_hfs_id_vg.txt', 'darwish_id_vg.txt', )#'bulk_hfs.txt', 'darwish_hfs.txt')
labels =('Bulk', 'Bulk and velocity saturation', 'Bulk + Surface with velocity saturation',)
syms = ('^k:', '+k:', 'xk:')
#syms = ('o--', '+--', '*--')
arrays = []
for i in files:
    data = pandas.read_csv(i, sep=" ")
    vdata = data.loc[abs(data['v(drain)'] - 0.1) < 1e-3]
    vgs = vdata['v(gate)']
    ids = vdata['it(drain)']
    arrays.append((vgs, ids))

for i, s in zip(arrays, syms):
    #plt.plot(*i, s)
    plt.semilogy(*i, s, linewidth=0.5)
#plt.plot(*arrays)
plt.legend(labels)
#plt.xlim(0, 1.0)
plt.xlabel('$V_{GS}$ (V)')
plt.ylabel('$I_{D}$ (A)')
plt.tick_params(axis='both', which='both', direction='in')
plt.savefig('idvg.eps', bbox_inches='tight', pad_inches=0)
plt.show()
