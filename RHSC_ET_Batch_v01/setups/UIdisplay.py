import os
import ipywidgets as widgets
from ipywidgets import Label, HBox, VBox
from ipyfilechooser import FileChooser

import collections

UISTYLE = {"description_width": "initial"}


def askPowerDensityRCfiles(topLabel=""):
    PWfc = FileChooser("./")   ### power file generated from FC
    MDfc = FileChooser("./")
    TFfc = FileChooser("./")
    PWType = widgets.RadioButtons(options=["IPF","CSV","TILE"], description="Power file type", disabled=False)
    HB1 = HBox([Label("Select Power File"), PWfc, PWType])
    HB2 = HBox([Label("Select Metal Density File"), MDfc])
    HB3 = HBox([Label("Select Totem TechFile"), TFfc])
    out = VBox([Label(topLabel), HB1, HB2, HB3])

    return out, [[PWfc, PWType], MDfc, TFfc]

def askDesignArea(topLabel=""):
    #style = {"description_width": "initial"}
    isManually = widgets.Select(options=["True", "False"], value="False", \
                                description="Design Area in Manually", style=UISTYLE, disabled=False)
    llx = widgets.FloatText(value=0.0, description="LLX", disabled=False)
    lly = widgets.FloatText(value=0.0, description="LLY", disabled=False)
    urx = widgets.FloatText(value=0.0, description="URX", disabled=False)
    ury = widgets.FloatText(value=0.0, description="URY", disabled=False)
    HB1 = HBox([llx, lly, urx, ury])
    out = VBox([Label(topLabel), isManually, HB1])
    
    return out, [isManually, llx, lly, urx, ury]

def askFileDropItems2Processing(title, fileQ, fileT=["ET_profile"], dropLabel="Select Thermal Profile:"):
    fileSelect = FileChooser("./")
    fileType = widgets.RadioButtons(options=fileT, description="Power file type", disabled=False)
    addBut = widgets.Button(description="Add", disable=False, style=UISTYLE)
    resetBut = widgets.Button(description="Reset", disable=False, style=UISTYLE)
    outWidget = widgets.Output()

    def add_button_clicked(b):
        inFile = False
        for _f in fileQ:
            if _f[0] == fileSelect.selected:
                inFile = True
                break
        
        if not inFile:
            fileQ.append((fileSelect.selected, fileType.value))
        
        outWidget.clear_output()
        with outWidget:
            print("Pending: {}".format(fileQ))
    
    def reset_button_clicked(b):
        fileQ.clear()
    
        outWidget.clear_output()
        with outWidget:
            print("Pending: {}".format(fileQ))
    
    addBut.on_click(add_button_clicked)
    resetBut.on_click(reset_button_clicked)

    HB1 = HBox([fileSelect, fileType, addBut, resetBut])
    HB2 = HBox([Label("Message:", style=UISTYLE), outWidget])
    out = VBox([Label(title), HB1, HB2])
    return out


def askDropItems2Processing(title, layerList, layerQ, dropLabel="Layers:"):
    #style = {"description_width": "initial"}
    layer_dropdown = widgets.Dropdown(options=layerList, description=dropLabel, style=UISTYLE)
    addBut = widgets.Button(description="Add", disable=False, style=UISTYLE)
    resetBut = widgets.Button(description="Reset", disable=False, style=UISTYLE)
    outWidget = widgets.Output()

    def add_button_clicked(b):
        layerQ.append(layer_dropdown.value)
    
        outWidget.clear_output()
        with outWidget:
            print("Pending: {}".format(layerQ))

    def reset_button_clicked(b):
        layerQ.clear()
    
        outWidget.clear_output()
        with outWidget:
            print("Pending: {}".format(layerQ))

    addBut.on_click(add_button_clicked)
    resetBut.on_click(reset_button_clicked)

    HB1 = HBox([layer_dropdown, addBut, resetBut])
    HB2 = HBox([Label("Message:", style=UISTYLE), outWidget])
    out = VBox([Label(title), HB1, HB2])
    return out

def setupMetalDensitybyGivenCellIPF(GlobalMDList, LayerMDList, layerStack, cellList=[], FCObject=None):
    outWidget = widgets.Output()

    cells = widgets.Dropdown(options=cellList, description="Cell List:", style=UISTYLE)

    mdType = widgets.Dropdown(options=["Metal_global", "Via_global"], description="Key word:", style=UISTYLE)
    md1 = widgets.FloatText(value=0.0, description="MD(%):", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="150px"))
    addBut1 = widgets.Button(description="Add Global", disable=False, style=UISTYLE)

    layer = widgets.Dropdown(options=layerStack, description="Layer:", style=UISTYLE)
    md2 = widgets.FloatText(value=0.0, description="MD(%):", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="150px"))
    
    addBut2 = widgets.Button(description="Add Layer", disable=False, style=UISTYLE)
    resetBut = widgets.Button(description="Reset", disable=False, style=UISTYLE)
    
    def add_BT1_clicked(b):
        cellArea = FCObject.getCellsAreaList(cells.value)
        for a in cellArea:
            addStr = "{},{},{},{},{},{}".format(mdType.value,a[0],a[1],a[2],a[3],md1.value)
            GlobalMDList.append(addStr)
        
        outWidget.clear_output()
        with outWidget:
            print("Pending: Global #items={}".format(len(GlobalMDList)))
    
    def add_BT2_clicked(b):
        cellArea = FCObject.getCellsAreaList(cells.value)
        for a in cellArea:
            addStr = "{},{},{},{},{},{}".format(layer.value,a[0],a[1],a[2],a[3],md2.value)
            LayerMDList.append(addStr)
        
        outWidget.clear_output()
        with outWidget:
            print("Pending: Layers #items={}".format(len(LayerMDList)))

    def reset_button_clicked(b):
        GlobalMDList.clear()
        LayerMDList.clear()
    
        outWidget.clear_output()
        with outWidget:
            print("Clear, Global:{}, Layer:{}".format(GlobalMDList, LayerMDList))

    addBut1.on_click(add_BT1_clicked)
    addBut2.on_click(add_BT2_clicked)
    resetBut.on_click(reset_button_clicked)

    HB1 = HBox([mdType, md1, addBut1])
    HB2 = HBox([layer, md2, addBut2])
    HB3 = HBox([Label("Message:", style=UISTYLE), outWidget])
    out = VBox([Label("Cell Metal Density setup"), cells, HB1, HB2, resetBut, HB3])
    return out

def setupMetalDensityArea(GlobalMDList, LayerMDList, layerStack):
    outWidget = widgets.Output()
    
    mdType = widgets.Dropdown(options=["Metal_global", "Via_global"], description="Key word:", style=UISTYLE)
    llx1 = widgets.FloatText(value=0.0, description="LLX:", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="100px"))
    lly1 = widgets.FloatText(value=0.0, description="LLY:", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="100px"))
    urx1 = widgets.FloatText(value=0.0, description="URX:", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="100px"))
    ury1 = widgets.FloatText(value=0.0, description="URY:", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="100px"))
    md1 = widgets.FloatText(value=0.0, description="MD(%):", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="150px"))
    addBut1 = widgets.Button(description="Add Global", disable=False, style=UISTYLE)
    
    mdLayer = widgets.Dropdown(options=layerStack, description="Layer:", style=UISTYLE)
    llx2 = widgets.FloatText(value=0.0, description="LLX", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="100px"))
    lly2 = widgets.FloatText(value=0.0, description="LLY", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="100px"))
    urx2 = widgets.FloatText(value=0.0, description="URX", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="100px"))
    ury2 = widgets.FloatText(value=0.0, description="URY", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="100px"))
    md2 = widgets.FloatText(value=0.0, description="MD(%):", disabled=False, style=UISTYLE,
                            layout=widgets.Layout(width="150px"))
    addBut2 = widgets.Button(description="Add Layer", disable=False, style=UISTYLE)
    resetBut = widgets.Button(description="Reset", disable=False, style=UISTYLE)
    
    def add_BT1_clicked(b):
        addStr = "{},{},{},{},{},{}".format(mdType.value,llx1.value,lly1.value,urx1.value,ury1.value,md1.value)
        GlobalMDList.append(addStr)
        
        outWidget.clear_output()
        with outWidget:
            print("Pending: {}".format(GlobalMDList))
    
    def add_BT2_clicked(b):
        addStr = "{},{},{},{},{},{}".format(mdLayer.value,llx2.value,lly2.value,urx2.value,ury2.value,md2.value)
        LayerMDList.append(addStr)
        
        outWidget.clear_output()
        with outWidget:
            print("Pending: {}".format(LayerMDList))
    
    def reset_button_clicked(b):
        GlobalMDList.clear()
        LayerMDList.clear()
    
        outWidget.clear_output()
        with outWidget:
            print("Clear, Global:{}, Layer:{}".format(GlobalMDList, LayerMDList))
    
    addBut1.on_click(add_BT1_clicked)
    addBut2.on_click(add_BT2_clicked)
    resetBut.on_click(reset_button_clicked)

    HB1 = HBox([mdType, llx1, lly1, urx1, ury1, md1])
    VB1 = VBox([Label("Global Metal Density Setup"), HB1, addBut1])

    HB2 = HBox([mdLayer, llx2, lly2, urx2, ury2, md2])
    VB2 = VBox([Label("Layer Metal Density Setup"), HB2, addBut2])

    MSG = HBox([Label("Message:", style=UISTYLE), outWidget])
    out = VBox([VB1, VB2, resetBut, MSG])
    
    return out
    

def setupCTMResolution(topLabel=""):
    #style = {"description_width": "initial"}
    CTM_name = widgets.Text(value="CTM01", description="CTM Name", style=UISTYLE, disabled=False)
    CTM_resolution = widgets.IntText(value=1, description="CTM Resolution", style=UISTYLE, disabled=False)
    HB = HBox([CTM_resolution, Label("um")])
    out = VBox([Label(topLabel), CTM_name, HB])

    return out, [CTM_name, CTM_resolution]

def setupBumpBall(title, Gtype="ARRAY", defaultValues=[0.05, 0.01, 0.07, 0.07, 5, 5]):
    #style = {"description_width": "initial"}

    if Gtype == "ARRAY":
        _D = widgets.FloatText(value=defaultValues[0], description="Diameter", disabled=False)
        _H = widgets.FloatText(value=defaultValues[1], description="Height", disabled=False)
        _PX = widgets.FloatText(value=defaultValues[2], description="Pitch X", disabled=False)
        _PY = widgets.FloatText(value=defaultValues[3], description="Pitch Y", disabled=False)
        _AX = widgets.intText(value=defaultValues[4], description="Array X", disabled=False)
        _AY = widgets.intText(value=defaultValues[5], description="Array Y", disabled=False)

        COMP = collections.namedtuple("COMP", ["diameter", "height", "pitchX", "pitchY", "arrayX", "arrayY"])
        comp = COMP(_D, _H, _PX, _PY, _AX, _AY)

        HB1 = HBox([_D, _H])
        HB2 = HBox([_PX, _PY])
        HB3 = HBox([_AX, _AY])
        out = VBox([Label(title), HB1, HB2, HB3])
        return out, comp

def setupBoundarys(defaultValues=[25.0, 1000, 10, 10]):
    ### default setting: ambient T, Top BC, Bot BC, Side BC ###
    #style = {"description_width": "initial"}

    AMBT = widgets.FloatText(value=defaultValues[0], description="Ambient T", disabled=False)
    TOPBC = widgets.FloatText(value=defaultValues[1], description="Top BC", disabled=False)
    BOTBC = widgets.FloatText(value=defaultValues[2], description="Bot BC", disabled=False)
    SIDEBC = widgets.FloatText(value=defaultValues[3], description="Side BC", disabled=False)

    BC = collections.namedtuple("BC", ["ambT", "topBC", "botBC", "sideBC"])
    bcs = BC(AMBT, TOPBC, BOTBC, SIDEBC)

    HB1 = HBox([TOPBC, BOTBC, SIDEBC])
    out = VBox([Label("Boundary Conditions"), AMBT, HB1])
    return out, bcs


def setupComponent(title, componentType, defaultValues=[0.0, 0.0, 0.0]):
    #style = {"description_width": "initial"}

    if componentType in ["MC", "LID", "TIM"]:
        _L = widgets.FloatText(value=defaultValues[0], description="Length", disabled=False)
        _W = widgets.FloatText(value=defaultValues[1], description="Width", disabled=False)
        _H = widgets.FloatText(value=defaultValues[2], description="Height", disabled=False)

        COMP = collections.namedtuple("COMP", ["length", "width", "height"])
        comp = COMP(_L, _W, _H)

        HB1 = HBox([_L, _W])
        out = VBox([Label(title), HB1, _H])
        return out, comp
    
    if componentType in ["PCB"]:
        _L = widgets.FloatText(value=defaultValues[0], description="Length", disabled=False)
        _W = widgets.FloatText(value=defaultValues[1], description="Width", disabled=False)

        COMP = collections.namedtuple("COMP", ["length", "width"])
        comp = COMP(_L, _W)

        HB1 = HBox([_L, _W])
        out = VBox([Label(title), HB1])
        return out, comp

def createArrayPanel(aX, aY, default=0.0):
    from ipywidgets import GridspecLayout

    def create_floatText(description, style={"description_width": "initial"}):
        return widgets.FloatText(value=default, description=description,
                                 style=style, layout=widgets.Layout(width="100px"))

    grid = GridspecLayout(aY, aX)

    for _y in range(aY):
        for _x in range(aX):
            if (aY-_y)/10 < 1:
                _str = "0{}-{}".format(str(aY-_y), str(_x+1))
            else:
                _str = "{}-{}".format(str(aY-_y), str(_x+1))
            
            grid[_y, _x] = create_floatText(_str)

    return grid

def ArrayPanel2TileIPF(XX, YY, TSize, arrayPanel,
                     outputFolder="./", outputName="tileIPF.csv"):
    
    def __F2Sprecision(fval, precision=5):
        prec = "{:."+str(precision)+"f}"
        return prec.format(fval)

    ## value in mW ##
    LLX, LLY = 0.0, 0.0
    URX, URY = (XX*TSize), (YY*TSize)

    outStr = ["inst,cell,llx,lly,urx,ury,total_pwr"]

    totalPwr = 0.0
    idCount = 0
    for _y in range(YY):
        for _x in range(XX):
            pwr = arrayPanel[_y, _x].value
            llx = TSize*_x
            lly = TSize*(YY-_y-1)
            urx = TSize*(_x+1)
            ury = TSize*(YY-_y)
            #print("LL:({}, {}), UR:({}, {}), PWR:{}".format(llx, lly, urx, ury, pwr))
            totalPwr += pwr

            _str = "{},cell_{},{},{},{},{},{}".format(idCount+1, idCount+1, llx, lly, urx, ury, pwr)
            outStr.append(_str)
            idCount += 1
    
    print("BBOX: ({},{})-({},{}), Total Power: {} mW".format(LLX, LLY, URX, URY, totalPwr))
    if not os.path.isdir(outputFolder):
        os.makedirs(outputFolder, 0o755)
    
    outPath = os.path.join(outputFolder, outputName)
    with open(outPath, "w") as fid:
        fid.write("\n".join(outStr))
        
    return [LLX, LLY, URX, URY], outPath

