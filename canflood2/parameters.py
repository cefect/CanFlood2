'''
Created on Mar 4, 2025

@author: cef
'''
import os
from datetime import datetime
import pandas as pd

from .hp.vfunc import vfunc_cdf_chk_d


#===============================================================================
# generic params-------
#===============================================================================
fileDialog_filter_str="CanFlood2 database files (*.canflood2)" 

#===============================================================================
# directories and files-------
#===============================================================================
src_dir = os.path.dirname(os.path.dirname(__file__))
plugin_dir = os.path.dirname(__file__)
home_dir = os.path.join(os.path.expanduser('~'), 'CanFlood2')
os.makedirs(home_dir, exist_ok=True)

 


#===============================================================================
# autos--------
#===============================================================================
today_str = datetime.now().strftime("%Y%m%d")




#===============================================================================
# ProjDB==================================-------
#===============================================================================
project_parameters_template_fp = os.path.join(plugin_dir, 'project_parameters_template.csv')

project_db_schema_d = {
    '01_project_meta': None,
    '02_project_parameters': pd.read_csv(project_parameters_template_fp),

    }



#===============================================================================
# hazards: event metadata---------
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
# hazards: database------
#===============================================================================
hazDB_meta_template_fp = os.path.join(plugin_dir, 'hazDB_meta_template.csv')
hazDB_schema_d = {
    '04_haz_meta': pd.read_csv(hazDB_meta_template_fp),
    '05_haz_events': pd.DataFrame(df_columns)
    }



#add these to the project schema
for k,v in hazDB_schema_d.items():
    if v is None:
        project_db_schema_d[k] = None
    else:
        project_db_schema_d[k] = v.copy()
        
#add the hazard parameters to the project parameters
#project parameters is the complete state. hazard is a subset
project_db_schema_d['02_project_parameters'] = pd.concat(
    [project_db_schema_d['02_project_parameters'], hazDB_schema_d['04_haz_meta']])
        
#===============================================================================
# MODEL SUITE===================----------
#===============================================================================
#===============================================================================
# database schema
#===============================================================================
project_db_schema_d['03_model_suite_index'] =     pd.DataFrame(
            columns={
                #indexers
                'modelid': int,
                'category_code': str,
                'name': str,
                
                #suite display parameters
                'status': str,
                'asset_label': str,
                'consq_label': str,                
                  
                
                #model results
                'result_ead': float, #resulting integrated EAD                
                
            }
        )

#special table parameters
#these will be prefixed by the model name
projDB_schema_modelTables_d = {
    'table_parameters': None,  # name of parameter table: simple key, value for the parameters in the model config UI
    'table_finv': None,  # name of table for: asset inventory (scale, elev, tag, cap)
    'tabel_expos': None,  # name of table for: exposure data (columns; hazard event names, rows: assets, values: sampled raster)
    'table_gels': None,  # name of table for: ground elevation data (columns: dem name, rows: assets)
    'table_dmgs': None,  # name of table for: damage data (columns: hazard event names, rows: assets, values: exposure and curve intersect)
}

 

#model_table_parameters
model_parameters_template_fp = os.path.join(plugin_dir, 'model_parameters_template.csv')



projDB_schema_modelTables_d['table_parameters'] = pd.read_csv(
    model_parameters_template_fp, dtype={'value': str}).drop('note', axis=1)

#update the master schema
for key in projDB_schema_modelTables_d.keys():
    project_db_schema_d['03_model_suite_index'][key] = ''







#===============================================================================
# #consequence category lookup
#===============================================================================
consequence_category_d = {
    'c1': {
        'desc': 'People (Health and Safety)',
        'boxName': 'groupBox_MS_c1'
    },
    'c2': {
        'desc': 'People (Society)',
        'boxName': 'groupBox_MS_c2'
    },
    'c3': {
        'desc': 'Critical Infrastructure',
        'boxName': 'groupBox_MS_c3'
    },
    'c4': {
        'desc': 'Economy (Financial)',
        'boxName': 'groupBox_MS_c4'
    },
    'c5': {
        'desc': 'Environment',
        'boxName': 'groupBox_MS_c5'
    },
    'c6': {
        'desc': 'Culture',
        'boxName': 'groupBox_MS_c6'
    },
    'c7': {
        'desc': 'Government',
        'boxName': 'groupBox_MS_c7'
    }
}

#===============================================================================
# vulnerabiltiy functions---------
#===============================================================================
project_db_schema_d['06_vfunc_index'] = pd.DataFrame(columns={
    k:v for k,v in vfunc_cdf_chk_d.items() if not k in ['exposure']
    })

project_db_schema_d['07_vfunc_data'] = pd.DataFrame(columns={
    'tag': str,'exposure': float, 'impact': float
    })
        


 
 
