set RUN_DIR     <$RUN_DIR>
set NAME_CASE   <$NAME>
set CTMTD_PATH  <$CTMTD>
set CTMBD_PATH  <$CTMBD>
set CTMRDL_PATH <$CTMRDL>
set TD_LENGTH   <$TD_LENGTH>
set TD_WIDTH    <$TD_WIDTH>
set TD_HEIGHT   <$TD_HEIGHT>
set BD_LENGTH   <$BD_LENGTH>
set BD_WIDTH    <$BD_WIDTH>
set BD_HEIGHT   <$BD_HEIGHT>
set RDL_LENGTH  <$RDL_LENGTH>
set RDL_WIDTH   <$RDL_WIDTH>
set RDL_HEIGHT  <$RDL_HEIGHT>
set TTF         <$TTF>
set TFTD        <$TFTD>
set TFBD        <$TFBD>
set TFRDL       <$TFRDL>

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

### Create PCB ###
layout prototype create -pre ${RUN_DIR}/{$NAME_CASE}_et/layout/PCB/PCB.pre -size {-1, -1, 1, 1} -layers {M4, 0.07, 0, 20, V3, 0.1, 1, 5, M3, 0.035, 0, 90, V2, 0.1, 1, 5, M2, 0.035, 0, 90, V1, 0.1, 1, 5, M1, 0.07, 0, 20}
layout import -name PCB -file ${RUN_DIR}/{$NAME_CASE}_et/layout/PCB/PCB.pre
## Define PCB materials ##
layout setup material -model PCB -add -type dielectric -name SUB_DIEL -c 0.001
layout setup material -model PCB -name SUB_DIEL -thermal -ts 25 -k 0.2 -cp 0.6 -density 1.9
layout setup material -model PCB -add -type conductor -name SUB_CU -c 0.001
layout setup material -model PCB -name SUB_CU -thermal -ts 25 -k 400 -cp 0.4 -density 9
## per layer material assignment ##
layout setup layer -metal PCB -name M1 -type signal -cond_mat SUB_CU -diel_mat SUB_DIEL
layout setup layer -metal PCB -name V1 -type signal -cond_mat SUB_CU -diel_mat SUB_DIEL
layout setup layer -metal PCB -name M2 -type signal -cond_mat SUB_CU -diel_mat SUB_DIEL
layout setup layer -metal PCB -name V2 -type signal -cond_mat SUB_CU -diel_mat SUB_DIEL
layout setup layer -metal PCB -name M3 -type signal -cond_mat SUB_CU -diel_mat SUB_DIEL
layout setup layer -metal PCB -name V3 -type signal -cond_mat SUB_CU -diel_mat SUB_DIEL
layout setup layer -metal PCB -name M4 -type signal -cond_mat SUB_CU -diel_mat SUB_DIEL

### Create MC ###
layout special create -name MC -length 1mm -width 1mm -template other
layout setup part -add -name MC_Block -type other -size -0.5 -0.5 0.5 0.5 -thickness -model MC
layout setup component -add -name MC_Block -part MC_Block -model MC
layout setup material -model MC -add -type dielectric -name MC_MAT -c 0.001
layout setup material -model MC -name MC_MAT -thermal -ts 25 -k 1 -cp 0.5 -density 0.6
layout setup part -model MC -name MC_Block -mat MC_MAT

### Create TIM/LID ###
layout special create -name TIM -length 1mm -width 1mm -template other
layout setup part -add -name TIM_Block -type other -size -0.5 -0.5 0.5 0.5 -thickness 0.01 -model TIM
layout setup component -add -name TIM_Block -part TIM_Block -model TIM
layout setup material -model TIM -add -type dielectric -name TIM_MAT -c 0.001
layout setup material -model TIM -name TIM_MAT -thermal -ts 25 -k 1.5 -cp 0.1 -density 1.0
layout setup part -model TIM -name TIM_Block -mat TIM_MAT

layout special create -name LID -length 1mm -width 1mm -template other
layout setup part -add -name LID_Block -type other -size -0.5 -0.5 0.5 0.5 -thickness 0.2 -model LID
layout setup component -add -name LID_Block -part LID_Block -model LID
layout setup material -model LID -add -type dielectric -name LID_MAT -c 0.001
layout setup material -model LID -name LID_MAT -thermal -ts 25 -k 400 -cp 0.4 -density 1.0
layout setup part -model LID -name LID_Block -mat LID_MAT

### Create Bumps/Balls ###
layout connection create -name uBump -length ${BD_LENGTH}um -width ${BD_WIDTH}um
layout connection change -model uBump -array -position {0, 0} -pitch {0.01 0.01} -num {4, 4}
layout connection change -model uBump -center
layout connection change -model uBump -diameter 0.04 -all
layout connection change -model uBump -thickness 0.03

layout connection create -name C4 -length ${RDL_LENGTH}um -width ${RDL_WIDTH}um
layout connection change -model C4 -array -position {0, 0} -pitch {0.06 0.06} -num {8, 8}
layout connection change -model C4 -center
layout connection change -model C4 -diameter 0.1 -all
layout connection change -model C4 -thickness 0.06


### Import CTM ###
ctm import -model TD_CTM -path ${CTMTD_PATH}
ctm import -model BD_CTM -path ${CTMBD_PATH}
ctm import -model RDL_CTM -path ${CTMRDL_PATH}

### Create physical die ###
ctm model createdie -model TD_CTM -name TD -length ${TD_LENGTH}um -width ${TD_WIDTH}um -height ${TD_HEIGHT}um
ctm model createdie -model BD_CTM -name BD -length ${BD_LENGTH}um -width ${BD_WIDTH}um -height ${BD_HEIGHT}um
ctm model createdie -model RDL_CTM -name RDL -length ${RDL_LENGTH}um -width ${RDL_WIDTH}um -height ${RDL_HEIGHT}um

### Create new thermal analysis ###
analysis setup new -type TI -name STATIC_RUN

### Add blocks to thermal analysis ###
analysis object add -name STATIC_RUN -type PCB -object PCB -model PCB
analysis object add -name STATIC_RUN -type Physical_Die -object TD -model TD
analysis object add -name STATIC_RUN -type Physical_Die -object BD -model BD
analysis object add -name STATIC_RUN -type Physical_Die -object RDL -model RDL
analysis object add -name STATIC_RUN -type BallBump -object uBump -model uBump
analysis object add -name STATIC_RUN -type BallBump -object C4 -model C4
analysis object add -name STATIC_RUN -type Molding -object MC -model MC
analysis object add -name STATIC_RUN -type HeatSink -object TIM -model TIM
analysis object add -name STATIC_RUN -type HeatSink -object LID -model LID

### Assembly ###
analysis object setproperty -name STATIC_RUN -object PCB -setasbase

analysis connection add -name STATIC_RUN -baseobject C4 -baseinterface Bottom_Interface -refobject PCB -refinterface Top_Interface
analysis connection add -name STATIC_RUN -baseobject RDL -baseinterface Bottom_Interface -refobject C4 -refinterface Top_Interface
analysis connection add -name STATIC_RUN -baseobject uBump -baseinterface Bottom_Interface -refobject RDL -refinterface Top_Interface

analysis connection add -name STATIC_RUN -baseobject BD -baseinterface Bottom_Interface -refobject uBump -refinterface Top_Interface
analysis connection add -name STATIC_RUN -baseobject TD -baseinterface Bottom_Interface -refobject BD -refinterface Top_Interface

analysis connection add -name STATIC_RUN -baseobject MC -baseinterface Bottom_Interface -refobject RDL -refinterface Top_Interface
analysis connection add -name STATIC_RUN -baseobject TIM -baseinterface Bottom_Interface -refobject MC -refinterface Top_Interface
analysis connection add -name STATIC_RUN -baseobject LID -baseinterface Bottom_Interface -refobject TIM -refinterface Top_Interface

project save

### Simulation type = Static ###
analysis simulation control -name STATIC_RUN -simtype Static

### Assign power, materials BCs ###
analysis object setproperty -name STATIC_RUN -object DIE -powersource DIE_CTM

analysis simulation control -name STATIC_RUN -tf -file ${TTF}
analysis simulation control -name STATIC_RUN -tf -die TD -tfdie ${TFTD}
analysis simulation control -name STATIC_RUN -tf -die BD -tfdie ${TFBD}
analysis simulation control -name STATIC_RUN -tf -die RDL -tfdie ${TFRDL}

analysis simulation control -name STATIC_RUN -boundary -temperature ${AMBIENT_T}
analysis simulation control -name STATIC_RUN -boundary -boundarytype USER
#analysis simulation control -name STATIC_RUN -boundary -fixedbc -object DIE -layer DIE -topbc ${TOPBC}H -botbc ${BOTBC}H

### Run analysis ###
#analysis simulation run -name STATIC_RUN
#analysis simulation run -name STATIC_RUN -detail -die TD -quality accurate

#report new -type Thermal_Profile -name TProfile -analysis STATIC_RUN

#project save

#analysis simulation export -name STATIC_RUN -die TD -static -thermalprofile -outputfolder ${RUN_DIR}/${NAME_CASE}_et
#analysis simulation export -name STATIC_RUN -die BD -static -thermalprofile -outputfolder ${RUN_DIR}/${NAME_CASE}_et
#analysis simulation export -name STATIC_RUN -die RDL -static -thermalprofile -outputfolder ${RUN_DIR}/${NAME_CASE}_et