
'''
module for adding interfaces to a gmsh format file
'''

import mesh_convert
import yaml
import argparse


def find_interfaces(dimension, elements):
    '''
    For a list of elements:

    * break them up by physical number
    * find intersections in each region
    '''
    if not dimension in (2, 3):
        raise RuntimeError("Unexpected Dimension %d" % dimension)
    set_dict = {}
    for t in elements:
        # physical number, elementary id
        pnum = (t[-2], t[-1])
        if pnum not in set_dict:
            set_dict[pnum] = set([])
        the_set = set_dict[pnum]
        if dimension == 3: # tetrahedra volumes
            n = sorted(t[0:4])
            tuples_to_add = [
                tuple([n[0], n[1], n[2]]),
                tuple([n[0], n[1], n[3]]),
                tuple([n[0], n[2], n[3]]),
                tuple([n[1], n[2], n[3]]),
            ]
        elif dimension == 2: # triangle volumes
            n = sorted(t[0:3])
            tuples_to_add = [
                tuple([n[0], n[1]]),
                tuple([n[0], n[2]]),
                tuple([n[1], n[2]]),
            ]
        for u in tuples_to_add:
            if u in the_set:
                the_set.remove(u)
            else:
                the_set.add(u)
    pnums = sorted(set_dict.keys())
    boundaries = {}
    for i, pnum_i in enumerate(pnums):
        set1 = set_dict[pnum_i]
        for j in range(i+1, len(pnums)):
            pnum_j = pnums[j]
            # skip when elementary id matches
            if pnum_i[0] == pnum_j[0]:
                continue
            set2 = set_dict[pnum_j]
            intersection = set1.intersection(set2)
            if intersection:
                boundaries[(pnum_i, pnum_j)] = sorted(intersection)
    return boundaries


def delete_coordinates(dimension, coordinates, surfaces, volumes):
    '''
    Given a list of coordinates, surface and volume elements:

    * convert elements into vertices
    * renumber coordinates with orphaned vertices removed
    '''
    cmap = [None] * (len(coordinates) + 1)
    vertices = set([])

    if dimension == 2:
        slice_surface = slice(0,2)
        slice_volume = slice(0,3)
    elif dimension == 3:
        slice_surface = slice(0,3)
        slice_volume = slice(0,4)
    else:
        raise RuntimeError("Unhandled Dimension %d" % dimension)

    for t in surfaces:
        vertices.update(t[slice_surface])
    for t in volumes:
        vertices.update(t[slice_volume])

    vertices = sorted(vertices)

    for i, j in enumerate(vertices, 1):
        cmap[j] = i

    new_coordinates = [None] * len(vertices)
    for i, j in enumerate(vertices, 1):
        # this is a text string with the first digit being the enumeration
        c = coordinates[j-1].split()
        c[0] = str(i)
        new_coordinates[i-1] = " ".join(c)

    new_surfaces = [None] * len(surfaces)
    for i, t in enumerate(surfaces):
        # print t
        nv = [cmap[x] for x in t[slice_surface]]
        nv.extend(t[-2:])
        # print nv
        new_surfaces[i] = tuple(nv)

    new_volumes = [None] * len(volumes)
    for i, t in enumerate(volumes):
        nv = [cmap[x] for x in t[slice_volume]]
        nv.extend(t[-2:])
        new_volumes[i] = tuple(nv)

    return new_coordinates, new_surfaces, new_volumes


def get_next_elem_id(elem_ids):
    '''
    return a new unique elem id
    '''
    nid = max(elem_ids) + 1
    return nid


def get_next_phys_id(pname_map):
    '''
    return a new unique phys id
    '''
    nid = max(pname_map.keys()) + 1
    return nid


def delete_region_elements(dimension, pname_map, name, elements):
    '''
    filter out elements from deleted regions
    '''
    for k, v in pname_map.items():
        if v[1] == name:
            d = v[0]
            pnum = k
    if d != dimension:
        raise RuntimeError("Expecting %s to have dimension %d" % (name, dimension))
    new_elements = [x for x in elements if x[-2] != pnum]
    return new_elements


def get_name(name0, name1, name_priority, interface_names):
    '''
    return name of added interface
    picks names based on yaml file or priority index
    '''
    ret = None
    for i in interface_names:
        regions = i['regions']
        if name0 in regions and name1 in regions:
            ret = i['interface']
            break
    if ret:
        return ret
    if name0 in name_priority and name1 in name_priority:
        if name_priority.index(name0) < name_priority.index(name1):
            ret = "%s_%s" % (name0, name1)
        else:
            ret = "%s_%s" % (name1, name0)
    else:
        ret = "%s_%s" % tuple(sorted([name0, name1]))
    return ret


def process_elements(elements):
    '''
    converts input tetrahedra from strings to ints
    gets unique set of elementary ids
    '''
    int_elements = []
    elem_ids = set([])
    for t in elements:
        # process into ints
        ints = [int(x) for x in t]
        # read physical number
        if ints[-2] != 0:
            int_elements.append(ints[1:])
            elem_ids.add(ints[-1])
    return int_elements, elem_ids


def get_pname_map(gmsh_pnames):
    '''
    processes physical names from mesh format
    '''
    pname_map = {}
    for p in gmsh_pnames:
        data = p.split()
        dimension = int(data[0])
        index = int(data[1])
        name = data[2][1:-1]
        # print name
        pname_map[index] = (dimension, name)
    return pname_map


def get_interface_map(dimension, interfaces, pname_map, elem_ids, name_priority, interface_names, existing_interfaces):
    '''
    names for new interfaces
    '''
    interface_map = {}

    if dimension == 3:
        sl = slice(0,3)
    elif dimension == 2:
        sl = slice(0,2)
    else:
        raise RuntimeError("Unhandled Dimension %d" % dimension)

    new_priority = []

    for ei in existing_interfaces:
        phys_id = ei[-2]
        elem_id = ei[-1]
        if phys_id not in pname_map:
            continue;
        pname = pname_map[phys_id][1]
        if pname not in interface_map:
            interface_map[pname] = {
                'phys_id': phys_id,
                'elem_id': {},
            }
            new_priority.append(pname)
        if elem_id not in interface_map[pname]['elem_id']:
            interface_map[pname]['elem_id'][elem_id] = [] 
        interface_map[pname]['elem_id'][elem_id].append(sorted(ei[sl])) 
        #print(sorted(ei[sl]))

    for n in name_priority:
        if n not in new_priority:
            new_priority.append(n)



    # each new interface gets a new elementary id
    for i in sorted(interfaces.keys()):
        interface = interfaces[i]
        new_elem_id = get_next_elem_id(elem_ids)
        elem_ids.add(new_elem_id)

        name0 = pname_map[i[0][0]][1]
        name1 = pname_map[i[1][0]][1]

        new_name = get_name(name0, name1, name_priority, interface_names)
        if new_name not in interface_map:
            phys_id = get_next_phys_id(pname_map)
            pname_map[phys_id] = (dimension - 1, new_name)
            interface_map[new_name] = {
                'phys_id': phys_id,
                'elem_id': {},
            }
            interface_map[new_name]['elem_id'][new_elem_id] = interface
            print(new_name)
        else:
            raise RuntimeError("interface %s already exists" % new_name)
    return interface_map, new_priority


def get_surface_elements(interface_map):
    '''
    gets all of the surface elements based on vertices
    they are close to the form to being written out
    '''
    elements = []
    for i in sorted(interface_map.keys()):
        phys_id = interface_map[i]['phys_id']
        print("%s %d" % (i, phys_id))
        for elem_id in sorted(interface_map[i]['elem_id'].keys()):
            ielements = interface_map[i]['elem_id'][elem_id]
            print("  %d %d" % (elem_id, len(ielements)))
            for t in ielements:
                u = list(t)
                u.append(phys_id)
                u.append(elem_id)
                elements.append(tuple(u))
    return elements

def fix_surface_conflicts(dimension, surfaces, pname_map, name_priority):
    nmap = {}
    data = {}
    for phys_id, info in pname_map.items():
        if info[0] == (dimension - 1):
            data[phys_id] = []
            nmap[info[1]] = phys_id
    for s in surfaces:
        data[s[-2]].append(s)

    if dimension == 3:
        sl = slice(0,3)
    elif dimension == 2:
        sl = slice(0,2)
    else:
        raise RuntimeError("Unhandled Dimension %d" % dimension)

    all_vertexes = set([])
    priority_vertexes = {}
    errors = ""
    for n in name_priority:
        if n not in nmap:
            continue
        nid = nmap[n]
        nset = set([])
        for s in data[nid]:
            nset.update(s[sl])
        intersection = all_vertexes.intersection(nset)
        if intersection:
            for lid, lvertexes in priority_vertexes.items():
                tmp = lvertexes.intersection(nset)
                if tmp:
                    hpname = pname_map[lid][1]
                    #errors += "overlapping elements between priority_name %s and boundary of higher priority %s\n" % (n, hpname)
                    errors += 'WARNING: boundaries "%s" and "%s" are touching at %d nodes\n' % (n, hpname, len(tmp))
        priority_vertexes[nid] = nset
        all_vertexes |= nset
    if errors:
        errors += "WARNING: this may cause issues when the boundaries are solving the same equations on the same regions\n" 
        print(errors)

    new_surfaces = []
    removed_surfaces = set([])
    for phys_id, elements in data.items():
        if phys_id in priority_vertexes:
            new_surfaces.extend(elements)
            continue

        other_boundaries = set([])
        local_new_elements = []
        local_vertexes = set([])
        
        for surface in elements:
            nset = set(surface[sl])
            if nset.intersection(all_vertexes):
                for lid, lvertexes in priority_vertexes.items():
                    tmp = lvertexes.intersection(nset)
                    if tmp:
                        other_boundaries.add('"%s"' % pname_map[lid][1])
            else:
                local_new_elements.append(surface)
                local_vertexes |= nset
        new_surfaces.extend(local_new_elements)
        all_vertexes |= local_vertexes
        priority_vertexes[phys_id] = local_vertexes
        kept = len(local_new_elements)
        removed = len(elements) - kept
        if removed > 0:
            print('INFO: removed %d/%d elements from generated surface "%s" for overlap with %s' % (removed, removed+kept, pname_map[phys_id][1], ", ".join(other_boundaries)))
        if kept == 0:
            print('INFO: generated surface "%s" removed for 0 elements' % pname_map[phys_id][1])
            removed_surfaces.add(phys_id)
    return new_surfaces, removed_surfaces



def delete_regions(dimension, regions_to_delete, pname_map, coordinates, surfaces, volumes):
    '''
    delete volume elements from specified regions
    then remove unneeded coordinates
    '''
    new_volumes = volumes[:]
    for r in regions_to_delete:
        new_volumes = delete_region_elements(dimension, pname_map, r, new_volumes)

    (new_coordinates, new_surfaces, new_volumes) = delete_coordinates(
        dimension, coordinates, surfaces, new_volumes)

    return new_coordinates, new_surfaces, new_volumes


def scale_coordinates(coordinates, scale):
    '''
    constant scale on all coordinate positions
    '''
    new_coordinates = [None] * len(coordinates)
    for i, c in enumerate(coordinates):
        e = c.split()
        v = [scale*float(x) for x in e[1:]]
        new_coordinates[i] = e[0] + " " + " ".join(["%1.15g" % x for x in v])
    return new_coordinates


def run(args):

    gmshinfo = mesh_convert.read_gmsh_info(args.input_mesh)

    yaml_map = {}
    if args.yaml:
        with open(args.yaml) as f:
            yaml_map = yaml.safe_load(f)
        print(yaml_map)

    for i in ('name_priority', 'interfaces', 'contact_regions'):
        if i not in yaml_map:
            yaml_map[i] = []

    outfile = args.output_mesh

    if gmshinfo['tetrahedra']:
        dimension = 3
        volumes, elem_ids = process_elements(gmshinfo['tetrahedra'])
        existing_surfaces, existing_surface_ids = process_elements(gmshinfo['triangles'])
        elem_ids |= existing_surface_ids
    elif gmshinfo['triangles']:
        dimension = 2
        volumes, elem_ids = process_elements(gmshinfo['triangles'])
        existing_surfaces, existing_surface_ids = process_elements(gmshinfo['edges'])
        elem_ids |= existing_surface_ids
    else:
        raise RuntimeError("Could not find 2D or 3D elements in mesh")

    interfaces = find_interfaces(dimension, volumes)

    # for i in sorted(interfaces.keys()):
    #  print(i, len(interfaces[i]))

    pname_map = get_pname_map(gmshinfo['pnames'])

    name_priority = yaml_map['name_priority']

    interface_names = yaml_map['interfaces']

    interface_map, interface_priority = get_interface_map(
        dimension, interfaces, pname_map, elem_ids, name_priority, interface_names, existing_surfaces)

    #interface_map = remove_connected_interface_elements(
    #    interface_map, name_priority
    #)

    surfaces = get_surface_elements(interface_map)

    surfaces, removed_surface_ids = fix_surface_conflicts(dimension, surfaces, pname_map, interface_priority)

    pnames = []
    for i in sorted(pname_map.keys()):
        if i in removed_surface_ids:
            continue
        x = '%d %d "%s"' % (pname_map[i][0], i, pname_map[i][1])
        print(x)
        pnames.append(x)

    # print(gmshinfo['pnames'])
    print(pnames)
    print(volumes[0])

    print(len(volumes))
    print(len(surfaces))

    regions_to_delete = [x['contact']
                     for x in yaml_map['contact_regions'] if x['remove']]

    coordinates = gmshinfo["coordinates"]
    (coordinates, surfaces, volumes) = delete_regions(
        dimension, regions_to_delete, pname_map, coordinates, surfaces, volumes)

    scale = 1.0
    try:
        scale = yaml_map['options']['scale']
    except KeyError:
        pass

    if scale != 1.0:
        coordinates = scale_coordinates(coordinates, scale)

    with open(outfile, "w") as ofh:
        mesh_convert.write_format_to_gmsh(ofh)
        mesh_convert.write_physical_names_to_gmsh(ofh, pnames)
        mesh_convert.write_nodes_to_gmsh(ofh, coordinates)
        empty_list = []
        if dimension == 2:
            mesh_convert.write_elements_to_gmsh(ofh, surfaces, volumes, empty_list)
        elif dimension == 3:
            mesh_convert.write_elements_to_gmsh(ofh, empty_list, surfaces, volumes)
        else:
            raise RuntimeError("Unhandled Dimension %d" % dimension)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='remove contact volumes and add interfaces and contacts')
    parser.add_argument('--input_mesh', help="input mesh", required=True)
    parser.add_argument('--output_mesh', help="output mesh", required=True)
    parser.add_argument('--yaml', help="input mesh", required=False)
    args = parser.parse_args()
    run(args)
