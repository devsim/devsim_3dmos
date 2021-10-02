import netCDF4
import numpy as np
import mesh_convert as mesh_convert

# from the draft manual online, but 0-based
tetra_numbering = [
  (0,1,3),
  (1,2,3),
  (0,2,3),
  (0,1,2),
]

triangle_numbering = [
  (-1, -1),
  (-1, -1),
  (0, 1),
  (1, 2),
  (2, 0),
]

def transform_ssdata(ssdata, blocks):
    '''
        Convert side set data from element sides to triangles
    '''
    out = [-1] * len(ssdata)
    for i, data in enumerate(ssdata):
        elem_index = data[0]
        elem_nodes = None
        for b in blocks:
            if elem_index <= b['max']:
                elem_nodes = b['elements'][elem_index - b['base']]
                if b['dimension'] == 3:
                    out[i] = np.array([elem_nodes[x] for x in tetra_numbering[data[1]]])
                elif b['dimension'] == 2:
                    out[i] = np.array([elem_nodes[x] for x in triangle_numbering[data[1]]])
                    print(data[1])
                    print(out[i])
                break
    return np.vstack(out)

def read_data(nc):
    x=nc.variables['coordx']
    y=nc.variables['coordy']
    z=nc.variables['coordz']
    coordinates=np.column_stack((x,y,z))

    num_el_blk = nc.dimensions['num_el_blk'].size

    ss_names = [i.compressed().tobytes().decode("utf-8") for i in nc.variables['ss_names']]
    eb_names = [i.compressed().tobytes().decode("utf-8") for i in nc.variables['eb_names']]
    coor_names = [i.compressed().tobytes().decode("utf-8") for i in nc.variables['coor_names']]

    blocks = []
    base = 1
    for i in range(num_el_blk):
        name = str(i+1)
        block = nc.variables['connect' + name]
        if block.elem_type == "TETRA":
            dimension = 3
        elif block.elem_type == "TRI3":
            dimension = 2
        else:
            raise RuntimeError("Block %s is not TETRA or TRI3" % i)

        if len(eb_names[i]) == 0:
            raise RuntimeError("Empty String for block")
        blocks.append({
            'name' : eb_names[i],
            'base' : base,
            'max'  : base + len(block)-1,
            'elements' : block[:].filled(),
            'dimension' : dimension,
        })
        base += len(block)

    # elements are numbered across all blocks
    num_side_sets = nc.dimensions['num_side_sets'].size
    #print(num_side_sets)
    side_sets = []
    for i in range(num_side_sets):
      name = str(i+1)
      ssdata = np.column_stack((nc.variables['elem_ss' + name][:], nc.variables['side_ss' + name][:] - 1))
      ssdata = transform_ssdata(ssdata, blocks)
      side_sets.append({
        'name' : ss_names[i],
        'elements' : ssdata
      })

    return {
      'coordinates' : coordinates.filled(),
      'side_sets' : side_sets,
      'blocks' : blocks
    }

def convert_to_gmsh_style(data):
    '''
    Converts to the gmsh representation used in other scripts
    '''
    pnames = []

    coordinates = []
    for i, c in enumerate(data['coordinates']):
        coordinates.append(str(i+1) + " " + " ".join([str(j) for j in c]))
    data['coordinates'] = coordinates

    tetrahedra = []
    triangles = []
    edges = []

    for i, b in enumerate(data['blocks']):
        j = i + 1
        dimension = b['dimension']
        pnames.append(" ".join([str(dimension), str(j), '"%s"' % b['name'] ]))

        if dimension == 3:
            # copy by reference
            fill = tetrahedra
        elif dimension == 2:
            fill = triangles

        for e in b['elements']:
            t = list(e)
            t.extend([j,j])
            fill.append(t)

    for i, s in enumerate(data['side_sets']):
        j = i + len(data['blocks']) + 1
        pnames.append(" ".join([str(s['elements'].shape[1]-1), str(j), '"%s"' % s['name'] ]))
        for e in s['elements']:
            t = list(e)
            t.extend([j,j])
            if len(e) == 3:
                triangles.append(t)
            elif len(e) == 2:
                edges.append(t)

    data['tetrahedra'] = tetrahedra
    data['triangles'] = triangles
    data['edges'] = edges

    data['physical_names'] = pnames
    return data



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Convert between Exodus and Gmsh format')
    parser.add_argument(
        '--gmsh',           help='the gmsh file for output', required=True)
    parser.add_argument(
        '--exodus',         help='the exodus file for input', required=True)
    parser.add_argument(
        '--scale',         help='scale', type=float, required=True)
    args = parser.parse_args()
    nc = netCDF4.Dataset(args.exodus)
    np.set_printoptions(threshold=100)
    data = read_data(nc)
    data['coordinates'] *= float(args.scale)
    print(data)
    gmsh_data = convert_to_gmsh_style(data)
    with open(args.gmsh, 'w') as ofh:
        mesh_convert.write_format_to_gmsh(ofh)
        mesh_convert.write_physical_names_to_gmsh(ofh, data['physical_names'])
        mesh_convert.write_nodes_to_gmsh(ofh, gmsh_data['coordinates'])
        mesh_convert.write_elements_to_gmsh(ofh, gmsh_data['edges'], gmsh_data['triangles'], gmsh_data['tetrahedra'])

