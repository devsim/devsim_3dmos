

L_G     =0.12
T_PLY   =0.3
T_OX    =0.0049

#$ T.LTO = low temp. oxide thickness
T_LTO  =0.025

#$ J.SD = source/drain junction depth
#$ L.SD = source/drain length
#$ RAT.SD = source/drain lateral junction ratio
#RAT.SD  n.val=0.0
#J.SD    n.val=0.05
L_SD =0.1

XMIN  =-L_G/2.-L_SD
XMAX  =L_G/2.+L_SD
YMIN  =-T_OX-T_PLY
YMAX  =0.6
# assume surface is at Y=0
YSURF = 0.0

#start with big oxide

import cubit
cubit.init([])


device_l = XMAX - XMIN
bulk_t = YMAX
depth = 0.025
oxide_l =  device_l
oxide_t = T_OX
gate_t = T_PLY
oxide_h = gate_t + oxide_t
gate_l = L_G

nitride_l = XMAX - (L_G/2. + T_LTO)
nitride_h = -(T_OX + T_LTO) - YMIN

blocks_create = (
  ('bulk',   (device_l, bulk_t,  depth), (0.0, +0.5*bulk_t,  0.0)),
  ('oxide',  (oxide_l,  oxide_h, depth), (0.0, -0.5*oxide_h, 0.0)),
  ('gate',   (gate_l,   gate_t,  depth), (0.0, -oxide_t - 0.5*gate_t, 0.)),
  ('nitride0',   (nitride_l,   nitride_h,  depth), (XMAX - nitride_l/2., YMIN + nitride_h/2., 0.0)),
  ('nitride1',   (nitride_l,   nitride_h,  depth), (XMIN + nitride_l/2., YMIN + nitride_h/2., 0.0)),
)

block_volumes = { }

for b in blocks_create:
    name, brick_data, move = b
    brick = cubit.brick(*brick_data)
    cubit.move(brick, move)
    block_volumes[name] = brick
    cubit.set_entity_name('volume', brick.id(), name)
    cubit.cmd('block %d add volume %d' %(brick.id(), brick.id()))
    cubit.cmd('block %d name "%s"' % (brick.id(), name))

cubit.cmd("remove overlap volume %d %d modify volume %d" % (block_volumes['oxide'].id(), block_volumes['gate'].id(), block_volumes['oxide'].id()))
cubit.cmd("remove overlap volume %d %d modify volume %d" % (block_volumes['oxide'].id(), block_volumes['nitride0'].id(), block_volumes['oxide'].id()))
cubit.cmd("remove overlap volume %d %d modify volume %d" % (block_volumes['oxide'].id(), block_volumes['nitride1'].id(), block_volumes['oxide'].id()))

rectangle_data = (
  ("source_contact", (L_SD/2., depth, "yplane"), (XMIN + L_SD/4., 0.0, 0.0), 'bulk'),
  ("drain_contact",  (L_SD/2., depth, "yplane"), (XMAX - L_SD/4.,  0.0, 0.0), 'bulk'),
#  ("gate_contact",   (L_G, depth, "yplane"),   (0, -oxide_h, 0), 'gate'),
  ("body_contact",   (device_l, depth, "yplane"), (0, +bulk_t, 0), 'bulk'),
  # FIND INTERFACES PROGRAMMATICALLY
  # NO NEED TO WORRY ABOUT SURFACE NODES INTERFACING NOTHING
)

body_data = {}

for r in rectangle_data:
    name, data, move, attach= r
    #print('create surface rectangle width %g height %g %s' % data)
    cubit.cmd('create surface rectangle width %g height %g %s' % data)
    i = cubit.get_last_id('body')
    cubit.cmd('body %d rename "%s_sb"' % (i, name))
    move_str = ''
    for j, k in enumerate('xyz'):
        print(j,k)
        if float(move[j]) != 0.0:
            move_str += " %s %g" % (k, float(move[j]))
    if move_str:
        cubit.cmd('body %d move %s' % (i, move_str))
        print('body %d move %s' % (i, move_str))
        #print('body %d %s_sb' % (i, name))
    body_data[name] = {'body' : cubit.body(i), 'volume' : block_volumes[attach]}
    #print(move_str)


cubit.cmd('imprint volume all')
cubit.cmd('merge volume all')

# contact boundary conditions
for i, name in enumerate(body_data.keys()):
    index = i + 1
    bd = body_data[name]
    vid = bd['volume'].id()
    for s in bd['body'].surfaces():
        sid = s.id()
        print('DDDDDD sideset %d add surface %d wrt volume %d' % (index, sid, vid))
        cubit.cmd('sideset %d add surface %d wrt volume %d' % (index, sid, vid))
    print('EEEEEE sideset %d name "%s"' % (index, name))
    cubit.cmd('sideset %d name "%s"' % (index, name))

# interface boundary conditions
interface_data = (
  ("gate_contact", "gate", "oxide"),
)

index = len(body_data.keys())+1
for name, r1, r2 in interface_data:
    s1 = set([x.id() for x in block_volumes[r1].surfaces()])
    s2 = set([x.id() for x in block_volumes[r2].surfaces()])
    intersections = list(s1.intersection(s2))
    for sid in intersections:
        cubit.cmd('sideset %d add surface %d wrt volume %d' % (index, sid, block_volumes[r1].id()))
    cubit.cmd('sideset %d name "%s"' % (index, name))
    index += 1

for name, ids in body_data.items():
    cubit.cmd('delete body %d' % (ids['body'].id()))

for i in ('bulk',):
    cubit.cmd("volume %d size auto factor 3" % block_volumes[i].id())
#    cubit.cmd("volume %d size auto factor 3" % block_volumes[i].id())
for i in ('oxide', 'gate', 'nitride0', 'nitride1'):
    cubit.cmd("volume %d size auto factor 5" % block_volumes[i].id())


cubit.cmd('''
save cub5 "cubit01.cub5" overwrite
delete mesh volume all propagate
volume all scheme tetmesh
volume all tetmesh growth_factor 1.5
set tetmesher optimize overconstrained tetrahedra on
set tetmesher optimize overconstrained edges on
set tetmesher optimize sliver on
set tetmesher optimize level 6
set tetmesher boundary recovery off
set tetmesher interior points on
mesh volume all
''')

cubit.cmd('set exodus netcdf4 on')
cubit.cmd('export mesh "cubit01.e" qualityfile overwrite')

