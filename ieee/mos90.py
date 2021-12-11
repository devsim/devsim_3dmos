
from newmodels.simple_physics import *
import newmodels.Klaassen as kla
import newmodels.mos_physics as mos_physics
from meshing import background_mesh
import devsim
import numpy as np
import csv
import math

device="mosfet"
silicon_regions=("bulk",)
oxide_regions=("oxide", "nitride0", "nitride1")
interfaces = ("bulk_oxide", "nitride0_oxide", "nitride1_oxide" )

regions = ("bulk", "oxide", "nitride0", "nitride1")
all_regions = list(regions)
all_regions.append("gate")

oxide_contacts = ('gate',)
silicon_contacts = ('source', 'drain', 'body')

def create_potential():
    for i in regions:
        CreateSolution(device, i, "Potential")
    CreateSolution(device, "gate", "Potential")
    ds.edge_model(device=device, region="gate", name="ElectricField", equation="0.0")

    for i in silicon_regions:
        SetSiliconParameters(device, i, 300)
        CreateSiliconPotentialOnly(device, i)

    #TODO nitride has different permittivity
    for i in oxide_regions:
        SetOxideParameters(device, i, 300)
        CreateOxidePotentialOnly(device, i, "default")

    ds.set_parameter(device=device, region="nitride0", name="Permittivity", value=7.5*eps_0)
    ds.set_parameter(device=device, region="nitride1", name="Permittivity", value=7.5*eps_0)

    for i in silicon_contacts:
        tmp = ds.get_region_list(device=device, contact=i)
        r = tmp[0]
        print("%s %s" % (r, i))
        CreateSiliconPotentialOnlyContact(device, r, i)
        ds.set_parameter(device=device, name=GetContactBiasName(i), value=0.0)

    # TODO: set workfunction difference!
    for i in oxide_contacts:
        tmp = ds.get_region_list(device=device, contact=i)
        CreateOxideContact(device=device, region=tmp[0], contact=i, vshift="gate_offset")
        ds.set_parameter(device=device, name=GetContactBiasName(i), value=0.0)
        ds.set_parameter(device=device, name="gate_offset", value=+0.6)

    for i in interfaces:
        CreateSiliconOxideInterface(device, i)

    attach_oxide_contacts()

def attach_oxide_contacts():
    fixpot = { }
    ox_coordinates = ds.get_node_model_values(device=device, region="oxide", name="coordinate_index")
    si_coordinates = ds.get_node_model_values(device=device, region="bulk", name="coordinate_index")
    for cox, csi in (('source_ox', 'source'), ('drain_ox', 'drain')):
        csets = []
        csets.append(set())
        csets.append(set())
        for i in ds.get_element_node_list(device=device, region="oxide", contact=cox):
            csets[0].update(i)
        for i in ds.get_element_node_list(device=device, region="bulk", contact=csi):
            csets[1].update(i)
        cmap = {}
        for i in csets[0]:
            cindex = ox_coordinates[i]
            cmap[cindex] = [i]
        for i in csets[1]:
            cindex = si_coordinates[i]
            cmap[cindex].append(i)
        fixpot[(cox, csi)] = cmap


    def myassemble(what, timemode):
        rcv=[]
        rv=[]
        if timemode != "DC":
            return [rcv, rv]

        oxeq = ds.get_equation_numbers(device=device, region="oxide", variable="Potential")
        sieq = ds.get_equation_numbers(device=device, region="bulk", variable="Potential")

        if  what != "MATRIXONLY":
            oxpo = ds.get_node_model_values(device=device, region="oxide", name="Potential")
            sipo = ds.get_node_model_values(device=device, region="bulk", name="Potential")
            for pair in (('source_ox', 'source'), ('drain_ox', 'drain')):
                cmap = fixpot[pair]
                for i, j in cmap.values():
                    rv.extend([oxeq[i], oxpo[i] - sipo[j]])
        if what !="RHS" :
            for pair in (('source_ox', 'source'), ('drain_ox', 'drain')):
                cmap = fixpot[pair]
                for i, j in cmap.values():
                    rcv.extend(
                        [
                            oxeq[i], oxeq[i], 1.0,
                            oxeq[i], sieq[i], -1.0,
                        ]

                    )
        #print(rcv)
        #print(rv)
        return rcv, rv, False

    # CREATE CONTACT EQUATIONS HERE
    # Add output charge later
    ds.contact_equation(device=device, contact="source_ox", name="PotentialEquation")
    ds.contact_equation(device=device, contact="drain_ox", name="PotentialEquation")

    ds.custom_equation(name="fixpotential", procedure=myassemble)

def setup_simple_dd():
    for i in silicon_regions:
        CreateSolution(device, i, "Electrons")
        CreateSolution(device, i, "Holes")
        ds.set_node_values(device=device, region=i, name="Electrons", init_from="IntrinsicElectrons")
        ds.set_node_values(device=device, region=i, name="Holes",     init_from="IntrinsicHoles")
        CreateSiliconDriftDiffusion(device, i, "mu_n", "mu_p")

    for c in silicon_contacts:
        tmp = ds.get_region_list(device=device, contact=c)
        r = tmp[0]
        CreateSiliconDriftDiffusionAtContact(device, r, c)

def setup_low_field_dd():
    for i in silicon_regions:
        CreateSolution(device, i, "Electrons")
        CreateSolution(device, i, "Holes")
        ds.set_node_values(device=device, region=i, name="Electrons", init_from="IntrinsicElectrons")
        ds.set_node_values(device=device, region=i, name="Holes",     init_from="IntrinsicHoles")

        kla.Set_Mobility_Parameters(device, i)
        kla.Klaassen_Mobility(device, i)
        #use bulk Klaassen mobility
        CreateSiliconDriftDiffusion(device, i, "mu_bulk_e", "mu_bulk_h")

    for c in silicon_contacts:
        tmp = ds.get_region_list(device=device, contact=c)
        r = tmp[0]
        CreateSiliconDriftDiffusionAtContact(device, r, c)

def setup_eeb_dd(model, hfs):
    '''
    element based simulation
    model: bulk, darwish
    hfs:   (True, False) high field saturation

    hole simulation is bulk only for this demonstration
    '''
    if model not in ('bulk', 'darwish'):
        raise RuntimeError('model must be "bulk" or "darwish"')

    for r in silicon_regions:
        #create normal currents
        mos_physics.CreateNormalElectricFieldFromCurrentFlow(device, r, "ElectronCurrent")
        mos_physics.CreateNormalElectricFieldFromCurrentFlow(device, r, "HoleCurrent")

        edrive = "ElectricField"

        gradEFn = "ElectricField + V_t*log(Electrons@n1/Electrons@n0)*EdgeInverseLength"

        CreateEdgeModel(device, r, "GEFN", gradEFn)
        CreateEdgeModel(device, r, "GEFN:Potential@n0", "ElectricField:Potential@n0")
        CreateEdgeModel(device, r, "GEFN:Potential@n1", "ElectricField:Potential@n1")
        CreateEdgeModel(device, r, "GEFN:Electrons@n0", "-V_t*EdgeInverseLength/Electrons@n0")
        CreateEdgeModel(device, r, "GEFN:Electrons@n1", "V_t*EdgeInverseLength/Electrons@n1")


        ehfs = "GEFN"


        if model == "bulk":
            if not hfs:
                mos_physics.CreateElementElectronCurrent(device, r, "ElementElectronCurrent", "mu_bulk_e", edrive)
                mos_physics.CreateElementElectronContinuityEquation(device, r, "ElementElectronCurrent")
            else:
                kla.Philips_VelocitySaturation(device, r, "mu_vsat_e", "mu_bulk_e", ehfs, "vsat_e")
                mos_physics.CreateElementElectronCurrent(device, r, "ElementElectronCurrent", "mu_vsat_e", edrive)

            mos_physics.CreateElementElectronContinuityEquation(device, r, "ElementElectronCurrent")

            mos_physics.CreateElementHoleCurrent(device, r, "ElementHoleCurrent", "mu_bulk_h", "ElectricField")
            mos_physics.CreateElementHoleContinuityEquation(device, r, "ElementHoleCurrent")
        elif model == "darwish":
            if not hfs:
                kla.Philips_Surface_Mobility(device, r, "Enormal_ElectronCurrent", "Enormal_HoleCurrent")
                mos_physics.CreateElementElectronCurrent(device, r, "ElementElectronCurrent", "mu_e_0", edrive)
            else:
                kla.Philips_Surface_Mobility(device, r, "Enormal_ElectronCurrent", "Enormal_HoleCurrent")
                kla.Philips_VelocitySaturation(device, r, "mu_vsat_e", "mu_e_0", ehfs, "vsat_e")
                mos_physics.CreateElementElectronCurrent(device, r, "ElementElectronCurrent", "mu_vsat_e", edrive)

            mos_physics.CreateElementElectronContinuityEquation(device, r, "ElementElectronCurrent")

            mos_physics.CreateElementHoleCurrent(device, r, "ElementHoleCurrent", "mu_bulk_h", "ElectricField")
            mos_physics.CreateElementHoleContinuityEquation(device, r, "ElementHoleCurrent")

    # do element models for both electrons and holes
    for contact in silicon_contacts:
        mos_physics.CreateElementContactElectronContinuityEquation(device, contact, "ElementElectronCurrent")
        mos_physics.CreateElementContactHoleContinuityEquation(device, contact, "ElementHoleCurrent")
#CreateElementModel(device, r, "mu_ratio", "mu_vsat_e/mu_bulk_e")
#CreateElementModel(device, r, "mu_surf_ratio", "mu_e_0/mu_bulk_e")
#CreateElementModel(device, r, "epar_ratio", "abs(Eparallel_ElectronCurrent/ElectricField_mag)")
#createElementElectronCurrent2d $device $region ElementElectronCurrent mu_n
#createElementElectronCurrent2d $device $region ElementElectronCurrent mu_bulk_e

def setup_refinement_collection():
    '''
    returns refinement collector
    '''

    node_indexes = {r : background_mesh.get_node_index(device=device, region=r) for r in regions}

    def get_silicon_model_values(device, region):
        '''
        returns a model for refinement of silicon regions
        '''
        node_index = node_indexes[region]

        potential = ds.get_node_model_values(device=device, region=region, name="Potential")
        electrons = ds.get_node_model_values(device=device, region=region, name="Electrons")
        test_model1 = [0.0] * len(node_index)
        test_model2 = [0.0] * len(node_index)
        for i, x in enumerate(node_index):
            diff = abs(potential[x[0]]-potential[x[1]])
            if diff > 0.075:
                test_model1[i] = 1
            elif diff < 0.005:
                test_model1[i] = -1

            diff = abs(math.log10(electrons[x[0]])-math.log10(electrons[x[1]]))
            if diff > 2:
                test_model2[i] = 1
            elif diff < 0.3010299956639812:
                test_model2[i] = -1

        test_model = background_mesh.max_merge_lists((test_model1, test_model2))

        return test_model

    def get_oxide_model_values(device, region):
        '''
        returns a model for non-refinement
        '''
        efield = ds.get_edge_model_values(device=device, region=region, name="ElectricField")
        test_model = [0.0] * len(efield)

        for i, x in enumerate(efield):
            diff = abs(x)
            if diff > 1e4:
                test_model[i] = 1
            elif diff < 10:
                test_model[i] = -1
        return test_model

    #pre populate empty lists into dict
    refinement_dict = {r : [] for r in all_regions}

    gate_node=ds.get_element_node_list(device=device, region="oxide", contact="gate")[0][0]

    def collectrefinements(device):
        nonlocal refinement_dict
        printAllCurrents(device)
        #printAllCurrents(device)
        for r in silicon_regions:
            refinement_dict[r].append(get_silicon_model_values(device=device, region=r))
        for r in oxide_regions:
            refinement_dict[r].append(get_oxide_model_values(device=device, region=r))
        refinement_dict["gate"].append(get_oxide_model_values(device=device, region="gate"))
        gate_potential = ds.get_node_model_values(device=device, region="oxide", name="Potential")[gate_node]
        ds.set_node_value(device=device, region="gate", name="Potential", value=gate_potential)

    return collectrefinements, refinement_dict

def printAllCurrents(device):
    outmap = {}
    for contact in oxide_contacts:
        v = ds.get_parameter(device=device, name=GetContactBiasName(contact))
        print("%s\t%g" % (contact, v))
        outmap[contact] = [v, 0.0, 0.0, 0.0]
    for contact in silicon_contacts:
        outmap[contact] = PrintCurrents(device, contact)
    return outmap


def create_csv_printer(csv_output):
    ofh = open(csv_output, 'a')
    writer = csv.writer(ofh, delimiter=' ')
    out_contacts = ('drain', 'gate', 'source', 'body')

    header = []
    for o in out_contacts:
        for i in ('v', 'ie', 'ih', 'it'):
            header.append('{0}({1})'.format(i, o))
    writer.writerow(header)

    def print_csv(device):
        nonlocal out_contacts
        nonlocal writer
        nonlocal ofh
        data = printAllCurrents(device)
        olist = []
        for contact in out_contacts:
            olist.extend(data[contact])
        writer.writerow(olist)
        ofh.flush()

    return print_csv

def get_node_refinements(refinement_dict, mincl, maxcl):
    node_refinements = {}
    for r in silicon_regions:
        mlist = background_mesh.max_merge_lists(refinement_dict[r])
        node_refinements[r] = background_mesh.get_node_refinements(device=device, region=r, model_values=mlist, mincl=mincl, maxcl=maxcl)
    for r in oxide_regions:
        mlist = background_mesh.max_merge_lists(refinement_dict[r])
        node_refinements[r] = background_mesh.get_node_refinements(device=device, region=r, model_values=mlist, mincl=mincl, maxcl=maxcl)

    mlist = background_mesh.max_merge_lists(refinement_dict["gate"])
    node_refinements["gate"] = background_mesh.get_node_refinements(device=device, region="gate", model_values=mlist, mincl=mincl, maxcl=maxcl)

    return node_refinements

def get_coordinate_refinements(node_refinements, maxcl, scale):
    coordinate_indexes = {}
    num_coordinates = -1
    for i in all_regions:
        ci = [int(x) for x in ds.get_node_model_values(device=device, region=i, name="coordinate_index")]
        coordinate_indexes[i] = ci
        num_coordinates = max(num_coordinates, max(ci))
    num_coordinates += 1

    coordinate_refinement = [maxcl]*num_coordinates
    print(num_coordinates)


    for r in all_regions:
        CreateSolution(device, r, "sizing")
        ds.set_node_values(device=device, region=r, name="sizing", values=node_refinements[r])
        for i, v in zip(coordinate_indexes[r], node_refinements[r]):
            cr = min(coordinate_refinement[i], v)
            #cr = math.pow(10., math.floor(math.log10(min(coordinate_refinement[i], v))))
            coordinate_refinement[i] = cr

    data = np.array(coordinate_refinement)*scale
    return data

def save_backup():
    # we are now at the initial bias
    biases = ('drain', 'gate', 'source', 'body')
    backup = {'regions' : {},
              'contacts' : {},
      }
    for i in oxide_regions:
        backup['regions'][i] = {}
        for j in ("Potential",):
            backup['regions'][i][j] = ds.get_node_model_values(device=device, region=i, name=j)
    for i in silicon_regions:
        backup['regions'][i] = {}
        for j in ("Potential", "Electrons", "Holes"):
            backup['regions'][i][j] = ds.get_node_model_values(device=device, region=i, name=j)
    backup['biases'] = {}
    for i in biases:
        backup['biases'][GetContactBiasName(i)] = ds.get_parameter(device=device, name=GetContactBiasName(i))
    return backup

def restore_backup(backup):
    for region, solution_data in backup['regions'].items():
        for name, values in solution_data.items():
            ds.set_node_values(device=device, region=region, name=name, values=values)
    for contact_bias, value in backup['biases'].items():
        print("RESTORE %s %g" % (contact_bias, value))
        ds.set_parameter(device=device, name=contact_bias, value=value)

