import os
from ansys.aedt.core import Hfss3dLayout
from ansys.aedt.core import Icepak

dx, dy = 1000, 1000
total_thickness = 4.22

if os.path.exists("./chip.aedt"):
    os.remove("./chip.aedt")
    
hfss = Hfss3dLayout("../EDB/chip.aedb", version="2025.1")
icepak = Icepak(version="2025.1")
icepak.solution_type = "SteadyState"
icepak.problem_type = "TemperatureOnly"
icepak.design_settings["ExportSettings"] = True


icepak.modeler.model_units = "um"
icepak.modeler.delete("Region")

cmp = icepak.create_pcb_from_3dlayout("U1", hfss.project_name, hfss.design_name, resolution=6)

print(cmp.name)

"""
sources = []
with open('c:/demo/power_map.txt') as f:
    for line in f:
        sources.append([float(i) for i in line.split()])
        
for m, i in enumerate(sources):
    for n, value in enumerate(i):
        cell = icepak.modeler.create_rectangle('XY', 
                                               (f'{m*dx}um', f'{n*dy}um', f'{4.25}um'),
                                               (f'{dx}um', f'{dy}um'))
        icepak.assign_source(cell.name, "Total Power", f'{value}mW', f's{m}_{n}')
        
processor = icepak.modeler.create_box((0, 0, f'{total_thickness}um'), 
                                      (10, 10, 0.2), 
                                      name = 'processor',
                                      material='silicon' )
icepak.assign_point_monitor_in_object(processor.name, monitor_name=f'monitor_{processor.name}')
processor.transparency = 0

dies = [
        icepak.modeler.create_box((12, 0, 0), (5, 5, 0.25), 'd1', 'silicon'),
        icepak.modeler.create_box((12, 6, 0), (5, 5, 0.25), 'd2', 'silicon'), 
        icepak.modeler.create_box((0, 12, 0), (5, 5, 0.25), 'd3', 'silicon'), 
        icepak.modeler.create_box((6, 12, 0), (5, 5, 0.25), 'd4', 'silicon'),
        ]


for die in dies:
    icepak.assign_source(die.name, "Total Power", '0.1W', f's_{die.name}')
    icepak.assign_point_monitor_in_object(die.name, monitor_name=f'monitor_{die.name}')
    die.transparency = 0

molding = icepak.modeler.create_box((-1, -1, 0), (19, 19, 1), 'molding','mold_material')

sub = icepak.materials.add_material('substate')
sub.thermal_conductivity = [35, 35, 3.5]
substrate = icepak.modeler.create_box((-1, -1, 0), (19, 19, -1), 'substrate', sub.name)

balls = []
for i in range(0, 17):
    for j in range(0, 17):
        ball = icepak.modeler.create_box((i+0.3, j+0.3, -1), (0.4, 0.4, -0.4), f'ball_{i}_{j}', 'copper')
        balls.append(ball)

pcb = icepak.modeler.create_rectangle('XY', (-1, -1, -1.4),  (19, 19))

icepak.assign_stationary_wall(molding.top_face_z.id, 
                              boundary_condition = "Heat Transfer Coefficient",
                              htc = "1000w_per_m2kel"
                              )
icepak.assign_stationary_wall(pcb.bottom_face_z.id, 
                              boundary_condition = "Heat Transfer Coefficient",
                              htc = "100w_per_m2kel"
                              )

priorities = [[molding.name, substrate.name],
              [b.name for b in balls],
              [d.name for d in dies] + [processor.name], 
              [cmp.name]]
"""

#icepak.mesh.assign_priorities(priorities)

setup = icepak.create_setup()
setup.props["Convergence Criteria - Energy"] = 1e-16
setup.props["Convergence Criteria - Max Iterations"] = 500
#icepak.analyze()
icepak.save_project()
icepak.close_project()