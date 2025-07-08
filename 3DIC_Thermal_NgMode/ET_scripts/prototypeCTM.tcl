set RUN_DIR     <$RUN_DIR>
set NAME_CASE   _CTM
set MODELNAME   CTMTI
set CTMNAME     <$CTMNAME>
set DIE_LENGTH  <$DIE_LENGTH>
set DIE_WIDTH   <$DIE_WIDTH>
set RESOLUTION  <$RESOLUTION>
set PWRMAP      <$PWRMAP>
set DENSITY     <$DENSITY>
set TOTEM_TF    <$TOTEM_TF>
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

ctm create -model ${MODELNAME} -area ${DIE_LENGTH} ${DIE_WIDTH} um
ctm import -model ${MODELNAME} -path ${PWRMAP}
mhs export -model ${MODELNAME} -folder ${CTMFOLDER} -name ${CTMNAME} -R ${RESOLUTION}um -type 1 -tf ${TOTEM_TF} -density ${DENSITY}
ctm view export -model ${MODELNAME} -file ${RUN_DIR}/CTM/ctm_pwr.png
