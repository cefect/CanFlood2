'''
Created on Mar 20, 2025

@author: cef

helpers for loading tutorial data to the ui
'''

import os
from ..parameters import src_dir
#===============================================================================
# parameters
#===============================================================================
test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
assert os.path.exists(test_data_dir)

widget_settings_d = {
    #model config dialog widget data related to specific tutorials
    'cf1_tutorial_02': {
        'comboBox_expoLevel':'depth-dependent (L2)',
        'comboBox_AI_elevType':'ground',
        'mFieldComboBox_cid':'xid',
        'mFieldComboBox_AI_01_scale':'f0_scale',
        'mFieldComboBox_AI_01_elev':'f0_elv',
        'mFieldComboBox_AI_01_tag':'f0_tag',
        'mFieldComboBox_AI_01_cap':'f0_cap',  
        'labelLineEdit_AI_label':'my inventory',
        'consequenceLineEdit_V':'some consequence',
        'comboBox_R_highPtail': 'none',
        'comboBox_R_lowPtail': 'extrapolate',
        'doubleSpinBox_R_lowPtail': 1e9,   
        'doubleSpinBox_R_highPtail': 0.1,
     
    },
    }


#===============================================================================
# functions
#===============================================================================
def get_test_data_filepaths_for_tutorials(
        search_dirs = ['cf1_tutorial_01', 'cf1_tutorial_02'],
        ):
    """for each tutorial, build a hierarchiceal dicationary of filepaths
    search the contents and assign based on filename"""
    
    data_lib = dict()
    for tutorial_name in search_dirs:
        tutorial_dir = os.path.join(test_data_dir, tutorial_name)
        assert os.path.exists(tutorial_dir), f'bad tutorial_dir: {tutorial_dir}'
        
        #build the dictionary
        d = dict()
        for root, dirs, files in os.walk(tutorial_dir):
            for file in files:

                if '~' in file:
                    continue

                #only include tif and geojson
                if file.endswith(('.tif', '.geojson', '.csv', '.xls')):
                    pass
                else:
                    continue
                
                
                
                
                #collect hazard rasters as a diicttionary keyed by the ARI
                if file.startswith('haz'):
                    assert file.endswith('.tif'), f'bad file: {file}'
                    if not 'haz' in d:
                        d['haz'] = dict()
                    ari = int(file.split('_')[1].split('.')[0])
                    d['haz'][ari] = os.path.join(root, file)
                    
                #collect the dem
                elif file.startswith('dem'):
                    assert file.endswith('.tif'), f'bad file: {file}'
                    d['dem'] = os.path.join(root, file)
                    
                #collect the aoi
                elif file.startswith('aoi'):
                    assert file.endswith('.geojson'), f'bad file: {file}'
                    d['aoi'] = os.path.join(root, file)
                    
                #collect the asset inventory (finv) layer
                elif file.startswith('finv'):
                    assert file.endswith('.geojson'), f'bad file: {file}'
                    d['finv'] = os.path.join(root, file)
                    
                #evals from CanFloodf1
                elif file.startswith('eventMeta'):
                    assert file.endswith('.csv'), f'bad file: {file}'
                    d['eventMeta'] = os.path.join(root, file)
                    
                elif file.startswith('vfunc'):
                    assert file.endswith('.xls'), f'bad file: {file}'
                    d['vfunc'] = os.path.join(root, file)
                    
                else:
                    raise IOError(f'unrecognized file: {file}')
                    
            data_lib[tutorial_name] = d
            
    return data_lib

tutorial_data_lib = get_test_data_filepaths_for_tutorials()