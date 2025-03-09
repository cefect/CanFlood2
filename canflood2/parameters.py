'''
Created on Mar 4, 2025

@author: cef
'''
import os
from datetime import datetime
import pandas as pd

#===============================================================================
# directories and files
#===============================================================================
src_dir = os.path.dirname(os.path.dirname(__file__))
plugin_dir = os.path.dirname(__file__)
home_dir = os.path.join(os.path.expanduser('~'), 'CanFlood2')
os.makedirs(home_dir, exist_ok=True)

#===============================================================================
# logging
#===============================================================================





#===============================================================================
# autos
#===============================================================================
today_str = datetime.now().strftime("%Y%m%d")


#===============================================================================
# project database
#===============================================================================
project_parameters_template_fp = os.path.join(plugin_dir, 'project_parameters_template.csv')

project_db_schema_d = {
    '01_project_meta': None,
    '02_project_parameters': None,

    '03_model_suite_index': pd.DataFrame(
            columns={
                'modelid': int,
                'category_code': str,
                'category_desc': str,
                'name': str,
                'result_ead': float, #resulting integrated EAD
                
                
                
            }
        )
    }

project_db_schema_nested_d = {
    'table_parameters': None,  # name of parameter table: simple key, value for the parameters in the model config UI
    'table_vfunc_index': None,  # name of table for: index of vfunc tables
    'table_finv': None,  # name of table for: asset inventory (scale, elev, tag, cap)
    'tabel_expos': None,  # name of table for: exposure data (columns; hazard event names, rows: assets, values: sampled raster)
    'table_gels': None,  # name of table for: ground elevation data (columns: dem name, rows: assets)
    'table_dmgs': None,  # name of table for: damage data (columns: hazard event names, rows: assets, values: exposure and curve intersect)
}

#add each entry from project_db_schema_nested_d as a string column to the project_db_schema_d['00_model_suite_index']
for key in project_db_schema_nested_d.keys():
    project_db_schema_d['03_model_suite_index'][key] = ''




model_parameters_template_fp = os.path.join(plugin_dir, 'model_parameters_template.csv')

project_db_schema_nested_d['table_parameters'] = pd.read_csv(model_parameters_template_fp)

#===============================================================================
# hazards: event metadata
#===============================================================================
# Control dictionary with metadata for each field, including display label, widget type, lock status, and dtype.
eventMeta_control_d = {
    "event_name": {
        "label": "Event Name",
        "widgetType": "string",
        "widgetLock": True,
        'widgetHide': False,
        "dtype": "str"
    },
    "prob": {
        "label": "Probability",
        "widgetType": "spinbox",
        "widgetLock": False,
        'widgetHide': False,
        "dtype": "float"
    },
    "metadata": {
        "label": "Metadata (optional)",
        "widgetType": "string",
        "widgetLock": False,
        'widgetHide': False,
        "dtype": "str"
    },
    "layer_id": {
        "label": "layer_id",
        "widgetType": "string",
        "widgetLock": True,
        'widgetHide': True,
        "dtype": "str"
    },
    "layer_fp": {
        "label": "layer_fp",
        "widgetType": "string",
        "widgetLock": True,
        'widgetHide': True,
        "dtype": "str"
    }
}

# Programmatically create the DataFrame template using the 'dtype' defined in the control dictionary.
df_columns = {}
for col, meta in eventMeta_control_d.items():
    df_columns[col] = pd.Series(dtype=meta["dtype"])
 

#===============================================================================
# hazards: database
#===============================================================================
hazDB_schema_d = {
    '04_haz_meta': None,
    '05_haz_events': pd.DataFrame(df_columns)
    }

hazDB_meta_template_fp = os.path.join(plugin_dir, 'hazDB_meta_template.csv')

#add these to the project schema
for k,v in hazDB_schema_d.items():
    if v is None:
        project_db_schema_d[k] = None
    else:
        project_db_schema_d[k] = v.copy()
        
 
 
#===============================================================================
# generic params
#===============================================================================
fileDialog_filter_str="CanFlood2 database files (*.canflood2)" 