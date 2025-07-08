set RUN_DIR     [pwd]
set NAME_CASE   CTM
set MODELNAME   TI1
set CTMNAME     CTM01
set DIEX        10.5
set DIEY        10.4
set RESOLUTION  1
set PWRMAP      /nfs/site/disks/ifs_itip_disk001/cchuang/Thermal/APR_Tflow/01.Data/mhs/pwd.mhs
set DENSITY     /nfs/site/disks/ifs_itip_disk001/cchuang/Thermal/APR_Tflow/01.Data/density.csv
set TOTEM_TF    /nfs/site/disks/ifs_itip_disk001/cchuang/Thermal/APR_Tflow/01.Data/tech/fake.tech
set CTMFOLDER   ${RUN_DIR}/CTM

if { [ info exists ::env(CURRENT_TESTCASE_RUN_ROOT_DIRECTORY) ] == 1 } {
    set RUN_DIR    $::env(CURRENT_TESTCASE_RUN_ROOT_DIRECTORY)
}
if { [ info exists ::env(CURRENT_TESTCASE_NAME) ] == 1 } {
    set NAME_CASE  $::env(CURRENT_TESTCASE_NAME)
}

project option set -flow 3DICTI
project new -name ${RUN_DIR}/${NAME_CASE}_et
project save

ctm create -model ${MODELNAME} -area ${DIEX} ${DIEY} um
ctm import -model ${MODELNAME} -path ${PWRMAP}
mhs export -model ${MODELNAME} -folder ${CTMFOLDER} -name ${CTMNAME} -R ${RESOLUTION}um -type 1 -tf ${TOTEM_TF} -density ${DENSITY}
