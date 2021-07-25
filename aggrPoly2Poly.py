# -*- coding: utf-8 -*-
import arcpy
from arcpy import env
# --- parameters --- #
arcpy.AddMessage("Grabbing parameters...")
SourceZone = arcpy.GetParameterAsText(0)
TargetZone = arcpy.GetParameterAsText(1)
AggregationField = arcpy.GetParameterAsText(2)
OutputFieldName = arcpy.GetParameterAsText(3)
VariableType = arcpy.GetParameterAsText(4)
AggregationType = arcpy.GetParameterAsText(5)


# --- setting temporary workspace --- #
arcpy.AddMessage("Setting workspace...")
#env.workspace = r"in_memory"
#env.workspace = r"D:\Users\Jan Zapletal\Documents\KGI\DP\DP_Projekt\DP_Projekt.gdb"
wrkspc = env.workspace
arcpy.AddMessage(wrkspc)
arcpy.env.overwriteOutput = True

Source_ShArea = "Source_ShAreaKm2"
Target_ShArea = "Target_ShAreaKm2"
Target_ObjectID_Fld = "Target_ObjectID"
Union_ShArea = "Union_ShAreaKm2"

# --- Creating temporary layers to avoid touching data attributes --- #
arcpy.AddMessage("Creating temporary layers...")
arcpy.FeatureClassToFeatureClass_conversion(SourceZone, wrkspc, "SourceZone_conv")
arcpy.FeatureClassToFeatureClass_conversion(TargetZone, wrkspc, "TargetZone_conv")

SourceZone_conv = arcpy.ListFeatureClasses("SourceZone_conv")[0]
TargetZone_conv = arcpy.ListFeatureClasses("TargetZone_conv")[0]
Target_ObjectID = arcpy.Describe(TargetZone_conv).OIDFieldName

# --- Creating necessary fields --- #
arcpy.AddMessage("Calculating areas...")
arcpy.AddField_management(SourceZone_conv, Source_ShArea, "DOUBLE")
arcpy.AddField_management(TargetZone_conv, Target_ShArea, "DOUBLE")
arcpy.AddField_management(TargetZone_conv, Target_ObjectID_Fld, "DOUBLE")

arcpy.CalculateGeometryAttributes_management(SourceZone_conv, [[Source_ShArea, "AREA"]], "", "SQUARE_KILOMETERS")
arcpy.CalculateGeometryAttributes_management(TargetZone_conv, [[Target_ShArea, "AREA"]], "", "SQUARE_KILOMETERS")
arcpy.CalculateField_management(TargetZone_conv, Target_ObjectID_Fld, "!"+Target_ObjectID+"!", "PYTHON3")

# --- Handling optional parameters --- #
if AggregationType == "":
    AggregationType = "SUM"
else:
    AggregationType = AggregationType

# --- Polygon overlay - Union method --- #
inFeatures = [SourceZone_conv, TargetZone_conv]
outFeatures = "Agg_Union"

arcpy.AddMessage("Polygon overlay...")
arcpy.Intersect_analysis(inFeatures, outFeatures, "ALL")
arcpy.AddField_management(outFeatures, Union_ShArea, "DOUBLE")
arcpy.CalculateGeometryAttributes_management(outFeatures, [[Union_ShArea, "AREA"]], "", "SQUARE_KILOMETERS")
arcpy.AddField_management(outFeatures, OutputFieldName, "DOUBLE")

# --- Counting population in feature segments --- #
arcpy.AddMessage("Calculating value for each segment...")
if VariableType == "EXTENSIVE":
    arcpy.AddMessage("Aggregating for EXTENSIVE value...")
    expression = "(!"+Union_ShArea+"! / !"+Source_ShArea+"!) * !"+AggregationField+"!"
    arcpy.CalculateField_management(outFeatures, OutputFieldName, expression, "PYTHON3")
    # --- Summaize segment values in target zone --- #
    arcpy.AddMessage("Calculating "+AggregationType+" for each target zone...")
    summaryTable = "summarize"
    arcpy.Statistics_analysis(outFeatures, summaryTable, [[OutputFieldName, AggregationType]], Target_ObjectID_Fld)
    # --- Joining aggregated data to the target layer --- #
    arcpy.AddMessage("Joining field to target zone layer...")
    arcpy.JoinField_management(TargetZone, Target_ObjectID, summaryTable, Target_ObjectID_Fld, [AggregationType+"_"+OutputFieldName])
    arcpy.AlterField_management(TargetZone, AggregationType+"_"+OutputFieldName, OutputFieldName, OutputFieldName)
elif VariableType == "INTENSIVE":
        expression = "!"+Union_ShArea+"! * !"+AggregationField+"!"
        arcpy.CalculateField_management(outFeatures, OutputFieldName, expression, "PYTHON3")
        cur = arcpy.UpdateCursor(outFeatures)
        for row in cur:
            if row.isNull(AggregationField)==True:
                cur.deleteRow(row)
        del cur
        del row
        # --- Summaize segment values in target zone --- #
        arcpy.AddMessage("Calculating "+AggregationType+" for each target zone...")
        summaryTable = "summarize"
        arcpy.Statistics_analysis(outFeatures, summaryTable, [[OutputFieldName, "SUM"],[Union_ShArea, "SUM"]], Target_ObjectID_Fld)
        arcpy.AddField_management(summaryTable, OutputFieldName, "DOUBLE")
        arcpy.CalculateField_management(summaryTable, OutputFieldName, "!SUM_"+OutputFieldName+"! / !SUM_"+Union_ShArea+"!", "PYTHON3")
        # --- Joining aggregated data to the target layer --- #
        arcpy.AddMessage("Joining field to target zone layer...")
        arcpy.JoinField_management(TargetZone, Target_ObjectID, summaryTable, Target_ObjectID_Fld, [OutputFieldName])

# --- Clear the temporary data --- #
arcpy.AddMessage("Deleting temporary layers...")
arcpy.Delete_management(outFeatures)
arcpy.Delete_management(SourceZone_conv)
arcpy.Delete_management(TargetZone_conv)
arcpy.Delete_management(summaryTable)

arcpy.AddMessage("Done! :)")
