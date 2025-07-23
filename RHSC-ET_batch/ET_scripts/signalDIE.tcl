set RUN_DIR     <$RUN_DIR>
set NAME_CASE   <$NAME>
set CTM_PATH    <$CTM>
set DIE_LENGTH  <$DIE_LENGTH>
set DIE_WIDTH   <$DIE_WIDTH>
set DIE_HEIGHT  <$DIE_HEIGHT>
set TTF         <$TTF>
set TFDIE       <$TFDIE>

set AMBIENT_T   <$AMBIENT_T>
set TOPBC       <$TOPBC>
set BOTBC       <$BOTBC>

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
ctm import -model DIE_CTM -path ${CTM_PATH}

### Create physical die ###
ctm model createdie -model DIE_CTM -name DIE -length ${DIE_LENGTH}um -width ${DIE_WIDTH}um -height ${DIE_HEIGHT}um

### Create new thermal analysis ###
analysis setup new -type TI -name STATIC_RUN

### Add blocks to thermal analysis ###
analysis object add -name STATIC_RUN -type Physical_Die -object DIE -model DIE

### Assembly ###
analysis object setproperty -name STATIC_RUN -object DIE -setasbase
project save

### Simulation type = Static ###
analysis simulation control -name STATIC_RUN -simtype Static

### Assign power, materials BCs ###
analysis object setproperty -name STATIC_RUN -object DIE -powersource DIE_CTM

analysis simulation control -name STATIC_RUN -tf -file ${TTF}
analysis simulation control -name STATIC_RUN -tf -die DIE -tfdie ${TFDIE}

analysis simulation control -name STATIC_RUN -boundary -temperature ${AMBIENT_T}
analysis simulation control -name STATIC_RUN -boundary -boundarytype USER
analysis simulation control -name STATIC_RUN -boundary -fixedbc -object DIE -layer DIE -topbc ${TOPBC}H -botbc ${BOTBC}H

### Run analysis ###
analysis simulation run -name STATIC_RUN
analysis simulation run -name STATIC_RUN -detail -die DIE -quality accurate

report new -type Thermal_Profile -name TProfile -analysis STATIC_RUN

project save

analysis simulation export -name STATIC_RUN -die DIE -static -thermalprofile -outputfolder ${RUN_DIR}/${NAME_CASE}_et