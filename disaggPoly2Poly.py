# -*- coding: utf-8 -*-
import arcpy
from arcpy import env

# --- setting temporary workspace --- #
arcpy.AddMessage("Setting workspace...")
#env.workspace = r"D:\Users\Jan Zapletal\Documents\KGI\DP\DP_Projekt\DP_Projekt.gdb"
#env.workspace = r"in_memory"
wrkspc = env.workspace
arcpy.AddMessage(wrkspc)
arcpy.env.overwriteOutput = True

# --- parameters --- #
arcpy.AddMessage("Grabbing parameters...")
SourceZone = arcpy.GetParameterAsText(0)
TargetZone = arcpy.GetParameterAsText(1)
DisaggregatedField = arcpy.GetParameterAsText(2)
OutputFieldName = arcpy.GetParameterAsText(3)
VariableType = arcpy.GetParameterAsText(4)
AncillaryLayer = arcpy.GetParameterAsText(5)
AncillaryFields = arcpy.GetParameterAsText(6)

# --- Setting field names --- #
Source_ShArea = "Source_ShAreaKm2"
Target_ShArea = "Target_ShAreaKm2"
Union_ShArea = "Union_ShAreaKm2"
Source_ObjectID_Fld = "Source_ObjectID"
Target_ObjectID_Fld = "Target_ObjectID"
Union_ObjectID_Fld = "Union_ObjectID"
WeightField = "Weight_Fld"
TempLayers = []

# --- Creating temporary layers to avoid touching data attributes --- #
SourceZone_conv = "SourceZone_conv"
TargetZone_conv = "TargetZone_conv"
AncillaryLayer_conv = "AncillaryLayer_conv"

#if AncillaryFields == "":
#    AncillaryLayer = ""

arcpy.AddMessage("Creating temporary layers...")
arcpy.FeatureClassToFeatureClass_conversion(SourceZone, wrkspc, SourceZone_conv)
arcpy.FeatureClassToFeatureClass_conversion(TargetZone, wrkspc, TargetZone_conv)
TempLayers.append(SourceZone_conv)
TempLayers.append(TargetZone_conv)

Source_ObjectID = arcpy.Describe(SourceZone_conv).OIDFieldName
Target_ObjectID = arcpy.Describe(TargetZone_conv).OIDFieldName
#arcpy.AddMessage(Source_ObjectID + ", "+ Target_ObjectID)

# --- Creating necessary fields --- #
arcpy.AddMessage("Calculating areas...")
arcpy.AddField_management(SourceZone_conv, Source_ShArea, "DOUBLE")
arcpy.AddField_management(TargetZone_conv, Target_ShArea, "DOUBLE")
arcpy.AddField_management(SourceZone_conv, Source_ObjectID_Fld, "DOUBLE")
arcpy.AddField_management(TargetZone_conv, Target_ObjectID_Fld, "DOUBLE")

arcpy.CalculateGeometryAttributes_management(SourceZone_conv, [[Source_ShArea, "AREA"]], "", "SQUARE_KILOMETERS")
arcpy.CalculateGeometryAttributes_management(TargetZone_conv, [[Target_ShArea, "AREA"]], "", "SQUARE_KILOMETERS")
arcpy.CalculateField_management(SourceZone_conv, Source_ObjectID_Fld, "!"+Source_ObjectID+"!", "PYTHON3")
arcpy.CalculateField_management(TargetZone_conv, Target_ObjectID_Fld, "!"+Target_ObjectID+"!", "PYTHON3")

# --- If ancillary fields are empty, it's not necessary to use an ancillary layer
if AncillaryLayer != "":
    arcpy.AddMessage("Ancillary Layer: " + AncillaryLayer)
    arcpy.FeatureClassToFeatureClass_conversion(AncillaryLayer, wrkspc, AncillaryLayer_conv)
    TempLayers.append(AncillaryLayer_conv)
    inFeatures = [SourceZone_conv, TargetZone_conv, AncillaryLayer_conv]
else:
    inFeatures = [SourceZone_conv, TargetZone_conv]

# --- Performing polygon overlay --- #
outFeatures = "Disagg_Union"
arcpy.AddMessage("Polygon overlay...")
#arcpy.Union_analysis(inFeatures, outFeatures, "ALL")
arcpy.Intersect_analysis(inFeatures, outFeatures, "ALL")
TempLayers.append(outFeatures)
arcpy.AddField_management(outFeatures, Union_ShArea, "DOUBLE")
arcpy.AddField_management(outFeatures, Union_ObjectID_Fld, "DOUBLE")
Union_ObjectID = arcpy.Describe(outFeatures).OIDFieldName
arcpy.CalculateField_management(outFeatures, Union_ObjectID_Fld, "!"+Union_ObjectID+"!", "PYTHON3")

Union_FeatureType = arcpy.Describe(outFeatures).shapeType
if Union_FeatureType == "Polygon":
    arcpy.CalculateGeometryAttributes_management(outFeatures, [[Union_ShArea, "AREA"]], "", "SQUARE_KILOMETERS")
elif Union_FeatureType == "Polyline":
    arcpy.CalculateGeometryAttributes_management(outFeatures, [[Union_ShArea, "LENGTH"]], "", "SQUARE_KILOMETERS")
elif Union_FeatureType == "Point":
    arcpy.CalculateField_management(outFeatures, Union_ShArea, "1" , "PYTHON3")
else:
    arcpy.AddError("Unsupported feature type!")
arcpy.AddMessage("Shape type of intersected layer is "+Union_FeatureType)
arcpy.AddField_management(outFeatures, WeightField, "DOUBLE")
arcpy.CalculateField_management(outFeatures, WeightField, 0, "PYTHON3")

# --- Variable type --- #
if VariableType == "EXTENSIVE":
    if AncillaryLayer != "": # if ancillary layer is provided
        if AncillaryFields != "":
            AncillaryF_Arr = AncillaryFields.split(";")
            for field in AncillaryF_Arr:
                FieldWeight = field.split(" ")
                if FieldWeight[1] == "" or FieldWeight[1] == "#":
                    FieldWeight[1] = "1"
                FieldWeight[1] = FieldWeight[1].replace(",",".")
                arcpy.CalculateField_management(outFeatures, WeightField, "!"+WeightField+"! + (!"+FieldWeight[0]+"! * "+FieldWeight[1]+")" , "PYTHON3")
        else:
            arcpy.CalculateField_management(outFeatures, WeightField, "1" , "PYTHON3")
        arcpy.CalculateField_management(outFeatures, WeightField, "!"+WeightField+"! * !"+Union_ShArea+"!" , "PYTHON3")
        arcpy.AddMessage("Summarizing ancillary data weights")
        summaryTable_anc = "summarize_anc"
        arcpy.Statistics_analysis(outFeatures, summaryTable_anc, [[WeightField, "SUM"]], Source_ObjectID_Fld)
        TempLayers.append(summaryTable_anc)
        # --- Joining aggregated data to the target layer --- #
        arcpy.AddMessage("Joining sum of weights to the source zone layer...")
        arcpy.JoinField_management(outFeatures, Source_ObjectID_Fld, summaryTable_anc, Source_ObjectID_Fld, ["SUM_"+WeightField])
        arcpy.AddField_management(outFeatures, "Union_"+OutputFieldName, "DOUBLE")
        arcpy.CalculateField_management(outFeatures, "Union_"+OutputFieldName, "!"+DisaggregatedField+"! * (!"+WeightField+"! / !SUM_"+WeightField+"!)" , "PYTHON3")
    else: # if ancillary layer is not provided
        arcpy.AddField_management(outFeatures, "Union_"+OutputFieldName, "DOUBLE")
        arcpy.CalculateField_management(outFeatures, "Union_"+OutputFieldName, "!"+DisaggregatedField+"! * (!"+Union_ShArea+"! / !"+Source_ShArea+"!)", "PYTHON3")
    arcpy.AddMessage("Aggregating data to each target zone...")
    summaryTable = "summarize"
    arcpy.Statistics_analysis(outFeatures, summaryTable, [["Union_"+OutputFieldName, "SUM"]], Target_ObjectID_Fld)
    TempLayers.append(summaryTable)
    arcpy.AddMessage("Joining field to target zone layer...")
    arcpy.JoinField_management(TargetZone, Target_ObjectID, summaryTable, Target_ObjectID_Fld, ["SUM_Union_"+OutputFieldName])
    try:
        arcpy.AlterField_management(TargetZone, "SUM_Union_"+OutputFieldName, OutputFieldName, OutputFieldName)
    except:
        arcpy.AddWarning("Field name "+OutputFieldName+" already exists! However, result was still joined...")
elif VariableType == "INTENSIVE":
    if AncillaryLayer != "": # if ancillary layer is provided
        if AncillaryFields != "":
            AncillaryF_Arr = AncillaryFields.split(";")
            for field in AncillaryF_Arr:
                FieldWeight = field.split(" ")
                if FieldWeight[1] == "" or FieldWeight[1] == "#":
                    FieldWeight[1] = "1"
                FieldWeight[1] = FieldWeight[1].replace(",",".")
                arcpy.CalculateField_management(outFeatures, WeightField, "!"+WeightField+"! + (!"+FieldWeight[0]+"! * "+FieldWeight[1]+")" , "PYTHON3")
        else:
            arcpy.CalculateField_management(outFeatures, WeightField, "1" , "PYTHON3")
        arcpy.CalculateField_management(outFeatures, WeightField, "!"+WeightField+"! * !"+Union_ShArea+"!" , "PYTHON3")
        mean_weight = "mean_weight"
        arcpy.Statistics_analysis(outFeatures, mean_weight, [[WeightField, "MEAN"]], Source_ObjectID_Fld)
        TempLayers.append(mean_weight)
        arcpy.JoinField_management(outFeatures, Source_ObjectID_Fld, mean_weight, Source_ObjectID_Fld, ["MEAN_"+WeightField])

        arcpy.AddField_management(outFeatures, "Union_"+OutputFieldName, "DOUBLE")
        arcpy.CalculateField_management(outFeatures, "Union_"+OutputFieldName, "!"+DisaggregatedField+"! * (!"+WeightField+"! / !MEAN_"+WeightField+"!)" , "PYTHON3")
    else: # if ancillary layer is not provided
        mean_area = "mean_area"
        arcpy.Statistics_analysis(outFeatures, mean_area, [[Union_ShArea, "MEAN"]], Source_ObjectID_Fld)
        TempLayers.append(mean_area)
        arcpy.JoinField_management(outFeatures, Source_ObjectID_Fld, mean_area, Source_ObjectID_Fld, ["MEAN_"+Union_ShArea])
        arcpy.AddField_management(outFeatures, "Union_"+OutputFieldName, "DOUBLE")
        arcpy.CalculateField_management(outFeatures, "Union_"+OutputFieldName, "!"+DisaggregatedField+"! * (!"+Union_ShArea+"! / !MEAN_"+Union_ShArea+"!)" , "PYTHON3")

    arcpy.AddMessage("Aggregating data to each target zone...")
    summaryTable = "summarize"

    arcpy.Statistics_analysis(outFeatures, summaryTable, [["Union_"+OutputFieldName, "SUM"],[Union_ShArea, "SUM"]], Target_ObjectID_Fld)
    TempLayers.append(summaryTable)
    arcpy.AddField_management(summaryTable, OutputFieldName, "DOUBLE")
    arcpy.CalculateField_management(summaryTable, OutputFieldName, "!SUM_Union_"+OutputFieldName+"! / !SUM_"+Union_ShArea+"!", "PYTHON3")
    # --- Joining aggregated data to the target layer --- #
    arcpy.AddMessage("Joining field to target zone layer...")
    arcpy.JoinField_management(TargetZone, Target_ObjectID, summaryTable, Target_ObjectID_Fld, [OutputFieldName])

    #arcpy.Statistics_analysis(outFeatures, summaryTable, [["Union_"+OutputFieldName, "MEAN"]], Target_ObjectID_Fld)
    #arcpy.AddMessage("Joining field to target zone layer...")
    #arcpy.JoinField_management(TargetZone, Target_ObjectID, summaryTable, Target_ObjectID_Fld, ["MEAN_Union_"+OutputFieldName])
    #arcpy.AlterField_management(TargetZone, "MEAN_Union_"+OutputFieldName, OutputFieldName, OutputFieldName)

arcpy.AddMessage("Deleting temporary layers...")
for feature in TempLayers:
    arcpy.Delete_management(feature)

arcpy.AddMessage("Done! :)")
