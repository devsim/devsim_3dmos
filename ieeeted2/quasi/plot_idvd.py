
import pandas
import matplotlib.pyplot as plt


#files = ('bulk.txt', 'bulk_hfs.txt', 'hfs_drain_sweep.txt')
#labels =('Bulk mobility', 'Bulk mobility with velocity saturation', 'Surface mobility with velocity saturation')
#syms = ('ok', '+k', 'xk')
#files = ('bulk_extended_vds_vg_1_vd_2.txt', 'bulk_hfs_extended_vds_vg_1_vd_2.txt', 'darwish_extended_vds_vg_1_vd_2.txt',)
files = ('bulk_id_vd.txt', 'bulk_hfs_id_vd.txt', 'darwish_id_vd.txt',)
#labels =('Bulk mobility', 'Bulk mobility with velocity saturation', 'Surface mobility with velocity saturation')
labels =('Bulk', 'Bulk and velocity saturation', 'Bulk + Surface with velocity saturation',)
syms = ('^k:', '+k:', 'xk:')
#syms = ('o--', '+--', '*--')
arrays = []
for i in files:
    data = pandas.read_csv(i, sep=" ")
    vdata = data.loc[(abs(data['v(gate)'] - 1) < 1e-3) & (data['v(drain)'] < 1.5)]
    print(vdata)
    vds = vdata['v(drain)']
    ids = vdata['it(drain)']
    arrays.append((vds, ids))

for i, s in zip(arrays, syms):
    plt.plot(*i, s, linewidth=0.5)
    #plt.plot(*i, s, markersize=5)
#plt.plot(*arrays)
#plt.legend(labels, loc="lower right")
plt.legend(labels, loc="upper left")
plt.ylim(0, 7e-5)
plt.xlabel('$V_{DS}$ (V)')
plt.ylabel('$I_{D}$ (A)')
plt.ticklabel_format(axis="y", style="sci", scilimits=(0,0), useMathText=True)
#plt.tick_params(axis='y', direction='in')
plt.tick_params(axis='both', which='both', direction='in')
plt.savefig('idvd.eps', bbox_inches='tight', pad_inches=0.1)
#plt.show()
