set RUN_DIR     <$RUN_DIR>
set NAME_CASE   <$NAME>
set CTMTD_PATH  <$TD_CTM>
set CTMBD_PATH  <$BD_CTM>
set TD_LENGTH   <$TD_LENGTH>
set TD_WIDTH    <$TD_WIDTH>
set TD_HEIGHT   <$TD_HEIGHT>
set BD_LENGTH   <$BD_LENGTH>
set BD_WIDTH    <$BD_WIDTH>
set BD_HEIGHT   <$BD_HEIGHT>

set TTF         <$TTF>
set TD_TF       <$TD_TF>
set BD_TF       <$BD_TF>

set AMBIENT_T   <$AMBIENT_T>
set TOPBC       <$TOPBC>
set BOTBC       <$BOTBC>
set SIDEBC      <$SIDEBC>

if { [ info exists ::env(CURRENT_TESTCASE_RUN_ROOT_DIRECTORY) ] == 1 } {
    set RUN_DIR    $::env(CURRENT_TESTCASE_RUN_ROOT_DIRECTORY)
}
if { [ info exists ::env(CURRENT_TESTCASE_NAME) ] == 1 } {
    set NAME_CASE  $::env(CURRENT_TESTCASE_NAME)
}
#### CASE RUN ENV SETUP ####
project option set -flow CPSTI
project new -name ${RUN_DIR}/${NAME_CASE}_et
project save

### Import CTM ###
ctm import -model TD_CTM -path ${CTMTD_PATH}
ctm import -model BD_CTM -path ${CTMBD_PATH}

### Create physical die ###
ctm model createdie -model TD_CTM -name TD -length ${TD_LENGTH}um -width ${TD_WIDTH}um -height ${TD_HEIGHT}um
ctm model createdie -model BD_CTM -name BD -length ${BD_LENGTH}um -width ${BD_WIDTH}um -height ${BD_HEIGHT}um

### Create new thermal analysis ###
analysis setup new -type TI -name STATIC_RUN

### Add blocks to thermal analysis ###
analysis object add -name STATIC_RUN -type Physical_Die -object TD -model TD
analysis object add -name STATIC_RUN -type Physical_Die -object BD -model BD

### Assembly ###
analysis object setproperty -name STATIC_RUN -object BD -setasbase
analysis connection add -name STATIC_RUN -baseobject TD -baseinterface Bottom_Interface -refobject BD -refinterface Top_Interface
project save

### Simulation type = Static ###
analysis simulation control -name STATIC_RUN -simtype Static

### Assign power, materials BCs ###
analysis object setproperty -name STATIC_RUN -object BD -powersource BD_CTM
analysis object setproperty -name STATIC_RUN -object TD -powersource TD_CTM

analysis simulation control -name STATIC_RUN -tf -file ${TTF}
analysis simulation control -name STATIC_RUN -tf -die TD -tfdie ${TD_TF}
analysis simulation control -name STATIC_RUN -tf -die BD -tfdie ${BD_TF}

analysis simulation control -name STATIC_RUN -boundary -temperature ${AMBIENT_T}

analysis simulation control -name STATIC_RUN -boundary -boundarytype USER
#analysis simulation control -name STATIC_RUN -boundary -enable {PKGTOP, PCBTOP, PKGSIDE, PCBBOTTOM, PCBSIDE} -pkgtop ${TOPBC} -pcbbottom ${BOTBC} -pcbtop ${SIDEBC} -pkgside ${SIDEBC} -pcbside ${SIDEBC}
analysis simulation control -name STATIC_RUN -boundary -fixedbc -object TD -layer TD -topbc ${TOPBC}H
analysis simulation control -name STATIC_RUN -boundary -fixedbc -object BD -layer BD -botbc ${BOTBC}H

### Run analysis ###
analysis simulation run -name STATIC_RUN
analysis simulation run -name STATIC_RUN -detail -die {TD, BD} -quality accurate

report new -type Thermal_Profile -name TProfile -analysis STATIC_RUN
project save

analysis simulation export -name STATIC_RUN -die TD -static -thermalprofile -outputfolder ${RUN_DIR}/${NAME_CASE}_et
analysis simulation export -name STATIC_RUN -die BD -static -thermalprofile -outputfolder ${RUN_DIR}/${NAME_CASE}_et
#analysis simulation export -name STATIC_RUN -die RDL -static -thermalprofile -outputfolder ${RUN_DIR}/${NAME_CASE}_et