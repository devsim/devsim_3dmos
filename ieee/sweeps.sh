#!/bin/bash
set -euxo pipefail

RESULTDIR=${PWD}/testdir
mkdir -p ${RESULTDIR}

(time python idvd.py --gmsh ./cubit02_interface.gmsh  --model bulk  --csv bulk_hfs_id_vd.txt --hfs ) |& tee ${RESULTDIR}/bulk_hfs_id_vd.out
(time python idvd.py --gmsh ./cubit02_interface.gmsh  --model darwish  --csv darwish_id_vd.txt --hfs ) |& tee ${RESULTDIR}/darwish_id_vd.out
(time python idvd.py --gmsh ./cubit02_interface.gmsh  --model bulk  --csv bulk_id_vd.txt --no-hfs ) |& tee ${RESULTDIR}/bulk_id_vd.out

(time python sweeps.py --gmsh ./cubit02_interface.gmsh  --model bulk  --csv bulk_id_vg.txt --no-hfs ) |& tee ${RESULTDIR}/bulk_id_vg.out
(time python sweeps.py --gmsh ./cubit02_interface.gmsh  --model bulk  --csv bulk_hfs_id_vg.txt --hfs ) |& tee ${RESULTDIR}/bulk_hfs_id_vg.out
(time python sweeps.py --gmsh ./cubit02_interface.gmsh  --model darwish  --csv darwish_id_vg.txt --hfs ) |& tee ${RESULTDIR}/darwish_id_vg.out

