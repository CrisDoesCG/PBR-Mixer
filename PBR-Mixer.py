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

# Create temp copy of materials for renamings etc...
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
            
        # Delete unused output nodes            
        if n.name() == "surface_output" or n.name() == "displacement_output":
            n.destroy()          
            
    # Copy the nodes from the temp materials to the new material
    newNodes = hou.copyNodesTo(tempMaterial.children(), newMaterial)

    
    # Create network box around each material's nodes
    box = newMaterial.createNetworkBox()
    box.setComment(selectedMaterials[index].name()) 
    box.setColor(hou.Color(randomColor()))
    for n in newNodes:
        box.addItem(n)
    box.fitAroundContents()   
    

    

# TODO: DELETE RELATIVE REFERENCES BEFORE COPY TO OTHER NETWORK
# TODO: ACTUAL LOGIC BEHIND CONNECTING STUFF

# Delete temp copy of materials
for t in tempMaterials:
    t.destroy()
