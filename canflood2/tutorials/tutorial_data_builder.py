'''
Created on Mar 20, 2025

@author: cef

helpers for loading tutorial data to the ui
'''

import os, re, pprint, copy
from ..parameters import src_dir
#===============================================================================
# parameters--------
#===============================================================================
test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
assert os.path.exists(test_data_dir)


#default tutorial 1 and 2 data
defaultt_data_d = {
    'haz': {        
        50: 'haz_0050.tif',
        100: 'haz_0100.tif',
        200: 'haz_0200.tif',
        1000: 'haz_1000.tif',
        },
    'dem': 'dem_rlay.tif',
    'aoi': 'aoi_vlay.geojson',
    'eventMeta': 'eventMeta_df.csv',
    'finv': 'finv_tut1a.geojson',
    
    }

#===============================================================================
# Tutorial 1 and 2 data
#===============================================================================

tutorial_lib = {
    'cf1_tutorial_01': { #L1 basic
        'fancy_name': 'Tutorial 1',
        'data': defaultt_data_d,
        'widget': {
            'Main_dialog': {
                #'studyAreaLineEdit': 'tutorial 1 area',
                #'userLineEdit': 'me?',
                'scenarioNameLineEdit': 'undefended',
                'climateStateLineEdit': 'historical climate', 
                'hazardTypeLineEdit': 'fluvial',
                'radioButton_ELari': '1',  # 0=False=AEP (not ARI)
            },
            'Model_config_dialog': {
                'comboBox_expoLevel': 'binary (L1)',
                'comboBox_AI_elevType': 'relative',
                'mFieldComboBox_cid': 'xid',
                'mFieldComboBox_AI_01_scale': 'f0_scale',
                'mFieldComboBox_AI_01_elev': 'f0_elv',
                # 'mFieldComboBox_AI_01_tag': None,
                # 'mFieldComboBox_AI_01_cap': None,
                'labelLineEdit_AI_label': 'my inventory',
                'consequenceLineEdit_V': 'some consequence',
                'comboBox_R_highPtail': 'none',
                'comboBox_R_lowPtail': 'extrapolate',
                'doubleSpinBox_R_lowPtail': 1e9,
                'doubleSpinBox_R_highPtail': 0.1,
            }
        }
    },
    
    'cf1_tutorial_02': { #L2 ARI
        'fancy_name': 'Tutorial 2a',
        'data': {**defaultt_data_d, **{
            'finv':'finv_tut2.geojson',
            'vfunc': 'vfunc.xls',
            }},
        
        'widget': {
            'Main_dialog': {
                #'studyAreaLineEdit': 'tutorial 2 area',
                #'userLineEdit': 'me?',
                'scenarioNameLineEdit': 'undefended',
                'climateStateLineEdit': 'historical climate',
                'hazardTypeLineEdit': 'fluvial',
                'radioButton_ELari': '1',  # 0=False=AEP (not ARI)
            },
            'Model_config_dialog': {
                'comboBox_expoLevel': 'depth-dependent (L2)',
                'comboBox_AI_elevType': 'relative',
                'mFieldComboBox_cid': 'xid',
                'mFieldComboBox_AI_01_scale': 'f0_scale',
                'mFieldComboBox_AI_01_elev': 'f0_elv',
                'mFieldComboBox_AI_01_tag': 'f0_tag',
                'mFieldComboBox_AI_01_cap': 'f0_cap',
                'labelLineEdit_AI_label': 'my inventory',
                'consequenceLineEdit_V': 'some consequence',
                'comboBox_R_highPtail': 'none',
                'comboBox_R_lowPtail': 'extrapolate',
                'doubleSpinBox_R_lowPtail': 1e9,
                'doubleSpinBox_R_highPtail': 0.1,
            }
        }
    }}

#===============================================================================
# Tutorial 2B (AEP)
#===============================================================================
# Copy the base tutorial 2 data to create a new tutorial 2b
tName = 'cf1_tutorial_02b'
tutorial_lib[tName] = copy.deepcopy(tutorial_lib['cf1_tutorial_02'])
tutorial_lib[tName]['fancy_name'] = 'Tutorial 2b (AEP)'
tutorial_lib[tName]['data'].update(
    {'eventMeta': 'eventMeta_df_aep.csv'}
    )
tutorial_lib[tName]['widget']['Main_dialog'].update(
    {'radioButton_ELari': '0'}
    )

#===============================================================================
# Tutorial 2C (finv heights)
#===============================================================================
tName = 'cf1_tutorial_02c'
tutorial_lib[tName] = copy.deepcopy(tutorial_lib['cf1_tutorial_02'])
tutorial_lib[tName]['fancy_name'] = 'Tutorial 2c (finv heights)'
tutorial_lib[tName]['data'].update(
    {'finv': 'finv_tut2_elev.geojson'}
    )
tutorial_lib[tName]['widget']['Model_config_dialog'].update(
    {'comboBox_AI_elevType': 'absolute'}
    )



 
 

#===============================================================================
# promote filename to filepahts
#===============================================================================
 
for tName in tutorial_lib.keys():
    for k, v in tutorial_lib[tName]['data'].copy().items():
        #convert un-nested values to filepath
        if isinstance(v, str):
            f = os.path.join(test_data_dir, v)
            tutorial_lib[tName]['data'][k] = f
            
            if not os.path.exists(f):
                raise AssertionError(f'bad filepath on {tName}.{k}')
            
        #convert nested values to filepath
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                f = os.path.join(test_data_dir, v2)
                tutorial_lib[tName]['data'][k][k2] = f
                
                if not os.path.exists(f):
                    raise AssertionError(f'bad filepath on {tName}.{k}.{k2}\n    {f}')
        else:
            raise KeyError('bad type')
        
#===============================================================================
# add proj DBs
#===============================================================================

# Search through each '.canflood2' file and append to the appropriate tutorial_lib 'proj_db' entry
proj_db_dir = os.path.join(test_data_dir, 'projDBs')
assert os.path.exists(proj_db_dir), f"Directory not found: {proj_db_dir}"

for filename in os.listdir(proj_db_dir):
    if filename.endswith('.canflood2'):
        tName = os.path.splitext(filename)[0]  # Get the name without the extension
        
        assert tName in tutorial_lib, f"Tutorial name '{tName}' not found in tutorial_lib"
        
        tutorial_lib[tName]['data']['projDB'] = os.path.join(proj_db_dir, filename)
            
#===============================================================================
# add fancy names   
#===============================================================================
#===============================================================================
# def format_fancy_tutorial_name(input_string):
#     if input_string =='cf1_tutorial_02b':
#         return 'Tutorial 2b'
#     
#     # Use regex to extract the tutorial number
#     match = re.search(r'tutorial_(\d+)', input_string)
#     if match:
#         tutorial_number = int(match.group(1))
#         return f'Tutorial {tutorial_number}'
#     else:
#         raise ValueError("Input string does not match the expected format")
#     
# for tName in tutorial_lib.keys():
#     tutorial_lib[tName]['fancy_name'] = format_fancy_tutorial_name(tName)
#     #print(f'{tName} -> {tutorial_lib[tName]["fancy_name"]}')
#     
#===============================================================================
#get fancy names lookup
tutorial_fancy_names_d = {
    tutorial_lib[tName]['fancy_name']: tName  for tName in tutorial_lib.keys()
    }

#===============================================================================
# over-write usernames
#===============================================================================
#change all usernames to '{tName} ({fancy_name})'
for tName, tut_data in tutorial_lib.items():
    fancy_name = tut_data['fancy_name']
    tut_data['widget']['Main_dialog']['studyAreaLineEdit'] = f'{tName} ({fancy_name})'
 
print(f'Loaded {len(tutorial_lib)} tutorials from \n    {test_data_dir}')
"""
pprint.pprint(tutorial_lib)
"""
                                     
                                     


 