# -*- coding: utf-8 -*-
import arcpy
from arcpy import env

# --- setting temporary workspace --- #
arcpy.AddMessage("Setting workspace...")
wrkspc = env.workspace
arcpy.AddMessage(wrkspc)
arcpy.env.overwriteOutput = True

# --- parameters --- #
arcpy.AddMessage("Grabbing parameters...")
SourcePoint = arcpy.GetParameterAsText(0)
TargetPolygon = arcpy.GetParameterAsText(1)
SummaryFields = arcpy.GetParameterAsText(2)
outFeatureClass = arcpy.GetParameterAsText(3)
#outFeatureClass = 'Target_SumWithin'
arcpy.AddMessage(SummaryFields)

arcpy.AddMessage("Summarizing input values...")
arcpy.SummarizeWithin_analysis(TargetPolygon, SourcePoint, outFeatureClass, 'KEEP_ALL', SummaryFields)
