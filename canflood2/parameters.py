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
project_db_schema_d = {
    'project_parameters': None,
    'project_meta': None,
    'model_suite_index': pd.DataFrame(
            columns={
                'modelid': int,
                'category_code': str,
                'category_desc': str,
                'name': str,
                'model_parameter_table_name': str,
            }
        )
    }


project_parameters_template_fp = os.path.join(plugin_dir, 'project_parameters_template.csv')