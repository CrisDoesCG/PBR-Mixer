# from __future__ import with_statement
import hou
import os
import random

def errorPrint(message, type, indents=0):
    if type == "i":       
        print("\t"*indents + "[INFO]: " + message)
    if type == "e":       
        print("\t"*indents + "[ERROR]: " + message)    
    if type == "s":       
        print("\t"*indents + "[SUCCES]: " + message)               
    if type == "d":       
        print("\t"*indents + "[DEBUG]: " + message)    

def randomColor():
    red = random.random()
    green = random.random()
    blue = random.random()

    return (red,green,blue)

# Get average position of selected nodes
def getAvgPos(nodes, offset):  
    sum_x = 0
    sum_y = 0

    for n in nodes:
        x, y = n.position()
        sum_x += x
        sum_y += y

    return (sum_x / len(nodes),sum_y / len(nodes) + offset)

def materialSelection():
    selectedNodes = hou.selectedNodes()

    if len(selectedNodes) < 2:
        errorPrint("You have to select more than one material!", "e")
        hou.ui.displayMessage("You have to select more than one material!")
        exit()
    else:
        valid = all(node.type().name() == "subnet" for node in selectedNodes)

        if valid == False:
            hou.ui.displayMessage("This is not a material!")   
            exit() 

        else:
            return selectedNodes

def materialNaming():
    userInput = hou.ui.readInput("Give your new material a name:", initial_contents="myMaterial", buttons=["Create material", "Close"])

    if userInput[0] == 1 or len(userInput[1]) == 0:
        errorPrint("Script has been closed.", "i")
        hou.ui.displayMessage("Script has been closed.")   
        exit()
    else:
        errorPrint(f"A material name has been chosen: {userInput[1]}", "s")
        return userInput[1]

# Create and connect surface_output node
def create_surfaceOutput(material, lastMix):
    output_surface = material.createNode("subnetconnector","surface_output")
    output_surface.parm("connectorkind").set("output")
    output_surface.parm("parmname").set("surface")
    output_surface.parm("parmlabel").set("Surface")
    output_surface.parm("parmtype").set("surface")
    output_surface.setInput(0, lastMix)

# Create and connect displacement_output node
def create_displacementOutput(material, lastMix):
    output_disp = material.createNode("subnetconnector","displacement_output")
    output_disp.parm("connectorkind").set("output")
    output_disp.parm("parmname").set("displacement")
    output_disp.parm("parmlabel").set("Displacement")
    output_disp.parm("parmtype").set("displacement") 
    output_disp.setInput(0, lastMix) 

print("------------------------------------------------")         
errorPrint("Starting PBR Mixer.","i")

# Check if there is a node called "surface_output" in each material
invalidMaterials = []
selectedMaterials = materialSelection()

for material in selectedMaterials:
    if all("surface_output" not in node.name() for node in material.children()):
        invalidMaterials.append(material.name())

# Print error message if true
if len(invalidMaterials) > 0:
    errorPrint("The following materials are missing a node called 'surface_output'\n","e")
    for im in invalidMaterials:
        errorPrint(im,"d",1)

    print_invalidMaterials = "\n\n".join(invalidMaterials)
    hou.ui.displayMessage(f"The following materials are missing a node called 'surface_output':\n\n{print_invalidMaterials}")   
    exit()

errorPrint("Materials seem ok, creating new material...", "s")



# Get info about for the new material
materialName = materialNaming()
materialPath = selectedMaterials[0].path()
materialRoot = os.path.dirname(materialPath)

errorPrint(f"A place for the material has been chosen: {materialRoot}","s")

# Create new material subnetwork
newMaterial = hou.node(materialRoot).createNode("subnet",materialName)
newMaterial.setPosition(hou.Vector2(getAvgPos(selectedMaterials,-3)))

# Create MTLX tab filter as parameter
parameters = newMaterial.parmTemplateGroup()

newParm_hidingFolder = hou.FolderParmTemplate("mtlxBuilder","MaterialX Builder",folder_type=hou.folderType.Collapsible)
newParam_tabMenu = hou.StringParmTemplate("tabmenumask", "Tab Menu Mask", 1, default_value=["MaterialX parameter constant collect null genericshader subnet subnetconnector suboutput subinput"])

newParm_hidingFolder.addParmTemplate(newParam_tabMenu)

parameters.append(newParm_hidingFolder)
newMaterial.setParmTemplateGroup(parameters) 

# Destroy pre-made nodes
for c in newMaterial.allSubChildren():
    c.destroy()

# Create temp maerial, copy of nodes and restructure etc...
tempMaterials = hou.copyNodesTo(selectedMaterials,hou.node(materialRoot))

for tempMaterial in tempMaterials:
    index = tempMaterials.index(tempMaterial)  

    for n in tempMaterial.children():        
        # Rename some nodes for better distinction        
        if n.name() == "UVAttrib" or n.name() == "UVControl":
            n.setName(n.name()+"_"+selectedMaterials[index].name())          
        
        # Set new poisitions        
        n.move(hou.Vector2(0,index*-25))

        # Delete relative paths
        for parm in n.parms():
            parm.deleteAllKeyframes()      
            
    # Copy the nodes from the temp materials to the new material
    newNodes = hou.copyNodesTo(tempMaterial.children(), newMaterial)
    
    # Create network box around each material's nodes
    box = newMaterial.createNetworkBox()
    box.setComment(selectedMaterials[index].name()) 
    box.setColor(hou.Color(randomColor()))
    for n in newNodes:
        box.addItem(n)
    box.fitAroundContents()   

# Actual conection logic
connectors = []    
    
for node in newMaterial.children():
    # Get the nodes that are connected to the surface_outputs inside a list, then delete them
    if "surface_output" in node.name():
        connectors.append(node.inputs()[0])
        node.destroy()        
        
# Create mixer nodes        
mixNodes = []        

while len(connectors)>1:     
    newMix = hou.node(newMaterial.path()).createNode("mtlxmix", f"{connectors[0]}_to_{connectors[1]}")
    mixNodes.append(newMix)
    
    newMix.moveToGoodPosition()
    
    newMix.setInput(0, connectors[0])
    newMix.setInput(1, connectors[1])
    
    del connectors[0:2]
    
    connectors.insert(0, newMix)


# Create output nodes and connect them to the last mixer nodes    
create_surfaceOutput(newMaterial, mixNodes[-1])
# create_displacementOutput(newMaterial)

# Delete temp copy of materials
for t in tempMaterials:
    t.destroy()
    
errorPrint(f"New material was created at: {newMaterial.path()}","s")
errorPrint(f"Ending script","i")
print("------------------------------------------------")    


# TODO: displacement logic
# pack up in definition
# loading bar?