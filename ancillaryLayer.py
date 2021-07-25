import arcpy
from arcpy import env

arcpy.env.overwriteOutput = True

arcpy.AddMessage("Grabbing input parameters...")
SourceZones = arcpy.GetParameterAsText(0)
Output = arcpy.GetParameterAsText(1)
SourceZone = SourceZones.split(';')

for value in SourceZone:
    arcpy.AddMessage(value)

arcpy.Union_analysis(SourceZones, Output, "ALL")
arcpy.AddMessage("Ancillary Layer successfully created!")
