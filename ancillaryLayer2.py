import arcpy
from arcpy import env

arcpy.env.overwriteOutput = True

arcpy.AddMessage("Grabbing input parameters...")
R_SourceZones = arcpy.GetParameterAsText(0)
R_Output = arcpy.GetParameterAsText(1)
R_CellSize = arcpy.GetParameterAsText(2)
R_CoordSys = arcpy.GetParameterAsText(3)
R_Extent = arcpy.GetParameterAsText(4)

arcpy.AddMessage(R_SourceZones)
arcpy.AddMessage(R_Output)
arcpy.AddMessage(R_CellSize)
arcpy.AddMessage(R_CoordSys)
arcpy.AddMessage(R_Extent)

if R_Extent != "":
    arcpy.env.workspace = R_Output

if R_Extent != "":
    arcpy.env.extent = R_Extent

if R_CoordSys != "":
    sr = arcpy.SpatialReference()
    sr.loadFromString(R_CoordSys)
    arcpy.env.outputCoordinateSystem = sr

R_SourceZone = R_SourceZones.split(";")
for layer in R_SourceZone:
    RasterPath = layer.split("'")[1::2]
    R_LayerField = layer.split(" ")
    if len(RasterPath) > 0:
        path = RasterPath[0]
    else:
        path = R_LayerField[0]
    arcpy.FeatureToRaster_conversion(path, R_LayerField[-1], R_LayerField[-1], R_CellSize)
