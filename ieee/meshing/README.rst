
==============
test_converter
==============

Description
-----------


Adds interfaces to a 2D or 3D structure created with Gmsh.  See ``run.sh`` for running an example structure.

An optional yaml file can be used to configure additional behavior.
Please see ``ring.yaml`` for an example.

Recommended Usage
-----------------

Create a .geo file with physical groups labeling volumes and surfaces.  The surfaces should denote contact boundary conditions.  Running the script will add interfaces.  It will also ensure that the interfaces do not share vertices with any other interfaces or contacts.

The input mesh must be created with the older Gmsh format.  Using ``examples/mobility/gmsh_mos2d.msh`` in the devsim distribution as an example:

::

  gmsh -2 -format 'msh2' gmsh_mos2d.geo


::

  python test_convert.py  --input_mesh gmsh_mos2d.msh  --output_mesh foo.msh 

The mesh can then be loaded in devsim for simulation.

::


The user should look in the updated msh file for the names:

::

  $PhysicalNames
  9
  1 1 "gate_contact"
  1 2 "gate_oxide_interface"
  1 4 "source_contact"
  1 5 "drain_contact"
  1 6 "body_contact"
  2 7 "gate"
  2 8 "oxide"
  2 9 "bulk"
  1 11 "bulk_oxide"
  $EndPhysicalNames

where the 1st column is the dimension of the physical group, and the last column is its name when loaded into devsim.

Troubleshooting
---------------

If the input mesh file has surfaces which overlap, it will print a warning:

::

  WARNING: boundaries "bulk_oxide_interface" and "drain_contact" are touching at 1 nodes
  WARNING: boundaries "source_contact" and "bulk_oxide_interface" are touching at 1 nodes
  WARNING: this may cause issues when the boundaries are solving the same equations on the same regions


Removing the ``bulk_oxide_interface`` physical name in the input file fixes the issue.  The resultant physical names are the same as the previous section, with these notices:

::

  INFO: removed 11/11 elements from generated surface "gate_oxide" for overlap with "gate_oxide_interface"
  INFO: generated surface "gate_oxide" removed for 0 elements
  INFO: removed 2/152 elements from generated surface "bulk_oxide" for overlap with "drain_contact", "source_contact"


Notice that 2 elements were removed from the ``bulk_oxide`` interface for conflicting with other boundary conditions, specifically ``source_contact`` and ``drain_contact``.  This is important because such overlaps can result in convergence issues in simulation.
