'''
Created on Jun 20, 2025

@author: cef

hadnling building/configuring of multi-model suites

Most testing should be in test_02_dialog_model.py and test_03_core.
    here, we focus on building multi-model suites for test_05_dialog_main_post
'''


import pytest, time, sys, inspect, os, shutil
import pprint


from canflood2.hp.qt import set_widget_value, get_widget_value
from canflood2.hp.basic import view_web_df as view


import tests.conftest as conftest
from .conftest import (
    conftest_logger, 
    result_write_filename_prep, click
    )




from tests.test_01_dialog_main import dialog_loaded
from tests.test_01_dialog_main import _04_MS_args, _04_MS_args_d



#===============================================================================
# DATA--------
#===============================================================================
test_data_dir = os.path.join(conftest.test_data_dir, 'dialog_model_multi')
os.makedirs(test_data_dir, exist_ok=True)


#===============================================================================
# HELPERS-----
#===============================================================================
overwrite_testdata_plugin=True 


overwrite_testdata=True #for writing tests
def write_projDB(dialog_main, test_name): 
    projDB_fp = dialog_main.get_projDB_fp()
    ofp = oj_out(test_name, projDB_fp)
 
    if overwrite_testdata:
        print(f'\n\nwriting projDB to \n    {test_name}\n{"="*80}')
        os.makedirs(os.path.dirname(ofp), exist_ok=True)
        
        #copy over the .sqlite file
        shutil.copyfile(projDB_fp, ofp) 
 
        conftest_logger.info(f'wrote result to \n    {ofp}')
        
        
        
def oj(*args):
    return os.path.join(test_data_dir, *args)

gfp = lambda x:oj(x, 'projDB.canflood2')

def oj_out(test_name, result):
    return oj(result_write_filename_prep(test_name, clear_str='dialog_model_multi_'), os.path.basename(result))
 
 
 
#===============================================================================
# FIXTURES--------
#===============================================================================



#===============================================================================
# TESTS---------
#===============================================================================




















