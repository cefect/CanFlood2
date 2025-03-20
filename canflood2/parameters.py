'''
Created on Mar 4, 2025

@author: cef
'''
import os, tempfile
from datetime import datetime
import pandas as pd
import numpy as np  

from .hp.vfunc import vfunc_cdf_chk_d
from .hp.sql import pd_dtype_to_sqlite_type


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

temp_dir = os.path.join(tempfile.mkdtemp(), 'CanFlood2')
os.makedirs(temp_dir, exist_ok=True)
 


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
    '02_project_parameters': pd.read_csv(project_parameters_template_fp,
                                         dtype = {'value': str}, #variable types
                                         ),

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
    '04_haz_meta': pd.read_csv(hazDB_meta_template_fp,
                               dtype = {'value': str}, #variable types
                               ),
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
    [project_db_schema_d['02_project_parameters'], hazDB_schema_d['04_haz_meta']]).reset_index(drop=True)
        
#===============================================================================
# MODEL SUITE===================----------
#===============================================================================
#===============================================================================
# database schema
#===============================================================================
 


project_db_schema_d['03_model_suite_index'] = pd.DataFrame({
                                'modelid': pd.Series(dtype='int'),
                                'category_code': pd.Series(dtype='str'),
                                'name': pd.Series(dtype='str'),
                                'asset_label': pd.Series(dtype='str'),
                                'consq_label': pd.Series(dtype='str'),
                                'result_ead': pd.Series(dtype='float')
                            })#.set_index(['modelid', 'category_code'] #doesnt seem like sqlite can handle multindex
                                        


"""
project_db_schema_d['03_model_suite_index'].dtypes
"""

#special table parameters

finv_index = pd.Index([], name='indexField', dtype=int)

#these will be prefixed by the model name
modelTable_params_d = {
    'table_parameters': {
        'df': pd.read_csv(
            os.path.join(plugin_dir, 'model_parameters_template.csv'),
            dtype={'value': str}
        ).drop('note', axis=1),
        'phase': 'compile',
        'allowed': {
                    'ead_rtail':['extrapolate', 'none', 'user'],
                    'ead_ltail':['flat', 'extrapolate', 'none', 'user'],    
                    },
    },
    'table_finv': {
        'df': pd.DataFrame({
            'nestID': pd.Series(dtype=int),
            'indexField': pd.Series(dtype=int),
            'scale': pd.Series(dtype=float),
            'elev': pd.Series(dtype=float),
            'tag': pd.Series(dtype=str),
            'cap': pd.Series(dtype=float)
        }),
        'phase': 'compile'
    },
    'table_expos': {
        'df': pd.DataFrame(index=finv_index),
        'phase': 'compile'
    },
    'table_gels': {
        'df': pd.DataFrame(
            {'dem_samples': pd.Series(dtype='float')},
            index=finv_index
        ),
        'phase': 'compile'
    },
    'table_dmgs': {
        'df': pd.DataFrame({
            'exposure': pd.Series(dtype=float),
            'impact': pd.Series(dtype=float),
            'impact_scaled': pd.Series(dtype=float),
            'impact_capped': pd.Series(dtype=float),
            'event_names': pd.Series(dtype=str), #index
            'nestID': pd.Series(dtype=int), #index
            'indexField': pd.Series(dtype=int) #index
        }),
        'phase': 'run'
    }
}

 
#get an extract of just the dataframes
projDB_schema_modelTables_d = {k: v['df'] for k, v in modelTable_params_d.items()}
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
# VFUCN==================---------
#===============================================================================

project_db_schema_d['06_vfunc_index'] = pd.DataFrame({
    k: pd.Series(dtype=v) for k, v in vfunc_cdf_chk_d.items() if not k in ['exposure', 'tag']
        },index=pd.Index([], name='tag', dtype=int))

project_db_schema_d['07_vfunc_data'] = pd.DataFrame({
    'tag': pd.Series(dtype=str),
    'exposure': pd.Series(dtype=float),
    'impact': pd.Series(dtype=float)
})

        

 
 
