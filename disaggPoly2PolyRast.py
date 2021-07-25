# -*- coding: utf-8 -*-
import arcpy
from arcpy import env
from arcpy.sa import *

# --- setting temporary workspace --- #
#arcpy.AddMessage("Setting temporary workspace...")
#env.workspace = r"D:\Users\Jan Zapletal\Documents\KGI\DP\DP_Projekt\DP_Projekt.gdb"

# --- parameters --- #
arcpy.AddMessage("Setting parameters...")
SourceZone = arcpy.GetParameterAsText(0)
TargetZone = arcpy.GetParameterAsText(1)
#env.workspace = arcpy.GetParameterAsText(2)
DisaggregatedField = arcpy.GetParameterAsText(2)
OutputFieldName = arcpy.GetParameterAsText(3)
VariableType = arcpy.GetParameterAsText(4)
CellSize = arcpy.GetParameterAsText(5)
AncillaryLayer = arcpy.GetParameterAsText(6)

#env.workspace = r"in_memory"
env.overwriteOutput = True
w = env.workspace

Source_ObjectID_Fld = "Source_ObjectID"
Target_ObjectID_Fld = "Target_ObjectID"
SourceZone_conv = "SourceZone_conv"
TargetZone_conv = "TargetZone_conv"
inFeatures = [SourceZone_conv, TargetZone_conv]
TempLayers = []

SZ_desc = arcpy.Describe(SourceZone)
TZ_desc = arcpy.Describe(TargetZone)

arcpy.AddMessage("Creating temporary layers...")
arcpy.FeatureClassToFeatureClass_conversion(SZ_desc.catalogPath, env.workspace, SourceZone_conv)
arcpy.FeatureClassToFeatureClass_conversion(TZ_desc.catalogPath, env.workspace, TargetZone_conv)
TempLayers.append(SourceZone_conv)
TempLayers.append(TargetZone_conv)

Source_ObjectID = arcpy.Describe(SourceZone_conv).OIDFieldName
Target_ObjectID = arcpy.Describe(TargetZone_conv).OIDFieldName

arcpy.AddField_management(SourceZone_conv, Source_ObjectID_Fld, "LONG")
arcpy.AddField_management(TargetZone_conv, Target_ObjectID_Fld, "LONG")

arcpy.CalculateField_management(SourceZone_conv, Source_ObjectID_Fld, "!"+Source_ObjectID+"!", "PYTHON3")
arcpy.CalculateField_management(TargetZone_conv, Target_ObjectID_Fld, "!"+Target_ObjectID+"!", "PYTHON3")

SZ_conv = SourceZone+"_rast"
arcpy.FeatureToRaster_conversion(SourceZone_conv, DisaggregatedField, SZ_conv, CellSize)
TempLayers.append(SZ_conv)
WeightRaster = "WeightRaster"
expression = 0

if AncillaryLayer != "":
    arcpy.AddMessage("Parsing Ancillary Layers and Weights from Input...")
    AncLayer = AncillaryLayer.split(";")
    length = len(AncLayer)
    #arcpy.AddMessage(length)
    for x in range(length):
        RasterPath = AncLayer[x].split("'")[1::2]
        FieldWeight = AncLayer[x].split(" ")
        #arcpy.AddMessage(RasterPath[0])
        if len(RasterPath) > 0:
            path = RasterPath[0]
        else:
            path = FieldWeight[0]
        if FieldWeight[-1] == "" or FieldWeight[-1] == "#":
            FieldWeight[-1] = "1"
        expression += Raster(path) * int(FieldWeight[-1])
    #arcpy.AddMessage(expression)

else:
    arcpy.AddMessage("Creating a constant weight raster...")
    outFeatures = "Disagg_Union"
    arcpy.Union_analysis(inFeatures, outFeatures, "ALL")

    Ancillary_conv = "Ancillary_conv"
    Ancillary_rast = arcpy.FeatureToRaster_conversion(outFeatures, arcpy.Describe(outFeatures).OIDFieldName, Ancillary_conv, CellSize)
    TempLayers.append(outFeatures)
    TempLayers.append(Ancillary_conv)
    TempLayers.append(Ancillary_rast)
    expression = Con(IsNull(Ancillary_rast), Ancillary_rast, 1)

expression.save(WeightRaster)
TempLayers.append(WeightRaster)

# --- Variable type --- #
if VariableType == "EXTENSIVE":
    arcpy.AddMessage("Variable Type = EXTENSIVE")

    arcpy.AddMessage("Performing Zonal Statistics")
    SumWeights = ZonalStatistics(SourceZone_conv, Source_ObjectID_Fld, WeightRaster, "SUM", "DATA")

    arcpy.AddMessage("Calculating value for each pixel...")
    expression2 = (Raster(WeightRaster) / Raster(SumWeights)) * Raster(SZ_conv)

    Target_ObjectID = arcpy.Describe(TargetZone_conv).OIDFieldName

    arcpy.AddMessage("Summarizing values within target zones...")
    SumValues_Table = "SumValues_Table"
    outZSaT = ZonalStatisticsAsTable(TargetZone_conv, Target_ObjectID_Fld, expression2, SumValues_Table, "DATA", "SUM")
    arcpy.AlterField_management(SumValues_Table, "SUM", OutputFieldName, OutputFieldName)
    TempLayers.append(SumValues_Table)

    arcpy.AddMessage("Joining result to the Target Zone layer...")
    arcpy.JoinField_management(TZ_desc.catalogPath, Target_ObjectID, SumValues_Table, Target_ObjectID_Fld, [OutputFieldName])
elif VariableType == "INTENSIVE":
    arcpy.AddMessage("Variable Type = INTENSIVE")

    arcpy.AddMessage("Performing Zonal Statistics")
    MeanWeights = ZonalStatistics(SourceZone_conv, Source_ObjectID_Fld, WeightRaster, "MEAN", "DATA")

    arcpy.AddMessage("Calculating value for each pixel...")
    expression2 = (Raster(WeightRaster) / Raster(MeanWeights)) * Raster(SZ_conv)

    Target_ObjectID = arcpy.Describe(TargetZone_conv).OIDFieldName

    arcpy.AddMessage("Summarizing values within target zones...")
    SumValues_Table = "SumValues_Table"
    outZSaT = ZonalStatisticsAsTable(TargetZone_conv, Target_ObjectID_Fld, expression2, SumValues_Table, "DATA", "SUM")
    TempLayers.append(SumValues_Table)
    arcpy.AddField_management(SumValues_Table, OutputFieldName, "DOUBLE")
    arcpy.CalculateField_management(SumValues_Table, OutputFieldName, "!SUM! / !COUNT!" , "PYTHON3")

    #arcpy.AlterField_management(SumValues_Table, "SUM", OutputFieldName, OutputFieldName)

    arcpy.AddMessage("Joining result to the Target Zone layer...")
    arcpy.JoinField_management(TZ_desc.catalogPath, Target_ObjectID, SumValues_Table, Target_ObjectID_Fld, [OutputFieldName])

arcpy.AddMessage("Deleting temporary layers...")
for feature in TempLayers:
    arcpy.Delete_management(feature)

arcpy.AddMessage("Done! :)")
