from abaqus import *
from abaqusConstants import *
import regionToolset

# Creating the Model
mdb.models.changeKey(fromName = 'Model-1', toName = 'Cantilever Beam')
beamModel = mdb.models['Cantilever Beam']

# Creating the Part
import sketch
import partition

beamProfileSketch = beamModel.ConstrainedSketch(name = 'Beam CS Profile', sheetSize = 200)
beamProfileSketch.rectangle(point1 = (-5,5), point2 = (5, -5))
dpt = float(4)
beamPart = beamModel.Part(name = 'Beam', dimensionality = THREE_D, type=DEFORMABLE_BODY)
beamPart.BaseSolidExtrude(sketch = beamProfileSketch, depth = dpt)



# Creating Material
import material

# Creating Sections
import section
SectNo = 4
for i in range (SectNo):
	beamMaterial = beamModel.Material(name = 'mater'+str(i))
	beamMaterial.Density(table = ((7872, ),))
	n = float(1)
	E_c = float(380e9)
	E_m = float(70e9)
	x = float((i+1)*(dpt/SectNo))
	a = float(dpt)
	E_var = E_m+(E_c-E_m)*(x/dpt)**n 
	p = beamPart
	ofst = (dpt/SectNo)
	datumId = p.DatumPlaneByPrincipalPlane(principalPlane=XYPLANE, offset = ofst*(i+1))
	c = p.cells
	face_pt_x = 0
	face_pt_y = 0
	face_pt_z = (i+1)*(dpt/SectNo) - ofst/2
	face_pt = (face_pt_x, face_pt_y, face_pt_z)
	datum_z_pt = (i)*(dpt/SectNo) + ofst/2
	datum_coord = (face_pt_x, face_pt_y, datum_z_pt)
	d1 = p.datums
	BaseCell = beamPart.cells.findAt((datum_coord,))
	if i == SectNo-1 :
	    region = p.Set(cells=BaseCell, name='Set-'+str(i))
	else :
	    part = p.PartitionCellByDatumPlane(datumPlane=d1[datumId.id], cells=BaseCell)
	    pickedCell = beamPart.cells.findAt((face_pt,))
	    region = p.Set(cells=pickedCell, name='Set-'+str(i))
	beamMaterial.Elastic(table = ((E_var, 0.29),))
	beamSection = beamModel.HomogeneousSolidSection(name = 'Beam Section '+str(i), material = 'mater'+str(i))
	beamPart.SectionAssignment(region = region, sectionName = 'Beam Section '+str(i))

# Creating the Assembly
import assembly

beamAssembly = beamModel.rootAssembly
beamInstance = beamAssembly.Instance(name = 'Beam Instance', part = beamPart, dependent = ON)

# Creating Step
import step

beamModel.StaticStep(name = 'Apply Load', previous = 'Initial', description = 'Load is applied during this step')

# Creating Field Output request
beamModel.fieldOutputRequests.changeKey(fromName = 'F-Output-1', toName = 'Selected Field Outputs')
beamModel.fieldOutputRequests['Selected Field Outputs'].setValues(variables = ('S', 'E', 'PEMAG', 'U', 'RF', 'CF'))
beamModel.HistoryOutputRequest(name = 'Default History Outputs', createStepName = 'Apply Load', variables = PRESELECT)
del beamModel.historyOutputRequests['H-Output-1']

# Applying the Load
top_face_pt_x = 0.2
top_face_pt_y = 0.1
top_face_pt_z = 2.5
top_face_pt = (top_face_pt_x, top_face_pt_y, top_face_pt_z)
# The face on which that point lies is the face we are looking for
top_face = beamInstance.faces.findAt((top_face_pt,))
# We extract the region of the face choosing which direction its normal points in
top_face_region=regionToolset.Region(side1Faces=top_face)
#Apply the pressure load on this region in the 'Apply Load' step
beamModel.Pressure(name='Uniform Applied Pressure', createStepName='Apply Load', region=top_face_region, distributionType=UNIFORM, magnitude=10, amplitude=UNSET) 

# Applying Boundry Condition
# Apply encastre (fixed) boundary condition to one end to make it cantilever I
# First we need to locate and select the top surface
# We place a point somewhere on the top surface based on our knowledge of the
# geometry
fixed_end_face_pt_x = 0.2
fixed_end_face_pt_y = 0
fixed_end_face_pt_z = 0
fixed_end_face_pt = (fixed_end_face_pt_x, fixed_end_face_pt_y, fixed_end_face_pt_z) 
fixed_end_face = beamInstance.faces.findAt((fixed_end_face_pt,))
 # we extract the region of the face choosing which direction its normal points in
fixed_end_face_region=regionToolset.Region(faces=fixed_end_face)
beamModel.EncastreBC(name='Encaster one end', createStepName='Initial', region=fixed_end_face_region)

# Creating the Mesh
import mesh 

beam_inside_xcoord = 0.2
beam_inside_ycoord = 0
beam_inside_zcoord = 2.5
elemType1 = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD, kinematicSplit=AVERAGE_STRAIN, secondOrderAccuracy=OFF, hourglassControl=DEFAULT, distortionControl=DEFAULT)
beamCells=beamPart.cells
selectedBeamCells=beamCells.findAt((beam_inside_xcoord, beam_inside_ycoord, beam_inside_zcoord),)
beamMeshRegion=(selectedBeamCells,)
beamPart.setElementType(regions=beamMeshRegion, elemTypes=(elemType1,))
beamPart.seedPart(size=0.1, deviationFactor=0.1)
beamPart.generateMesh()

# Creating and Running the Job
import job

mdb.Job(name='CantileverBeamJob', model='Cantilever Beam', type=ANALYSIS,
	explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, 
	description='Job simulates a loaded cantilever beam', 
	parallelizationMethodExplicit=DOMAIN, 
	multiprocessingMode=DEFAULT, 
	numDomains=1, userSubroutine='', numCpus=1, memory=50,
	memoryUnits=PERCENTAGE, scratch='', echoPrint=OFF, 
	modelPrint=OFF, contactPrint=OFF, historyPrint=OFF)

# Run the job
mdb.jobs['CantileverBeamJob'].submit(consistencyChecking=OFF)
# Do not return control till job is finished running
mdb.jobs['CantileverBeamJob'].waitForCompletion()
# End of run job 

# Post Processing
import visualization
beam_Odb_Path = 'CantileverBeamJob.odb'
an_Odb_object = session.openOdb(name = beam_Odb_Path)
