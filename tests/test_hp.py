'''
Created on Mar 18, 2025

@author: cef

testing some helper modules
'''


import os
import logging
import pytest
from pytest_qgis.utils import clean_qgis_layer


from qgis.core import QgsProcessingContext, QgsApplication, QgsProcessingFeedback, QgsRasterLayer, QgsProject
import processing
from processing.core.Processing import Processing

# Import your processing environment and custom feedback class.
from canflood2.hp.Q import ProcessingEnvironment

#===============================================================================
# data
#===============================================================================
"""simple borrow of filepaths from the tutorial data"""
from tests.data.tutorial_fixtures import tutorial_lib
tutorial_name = 'cf1_tutorial_02'
data_d = tutorial_lib[tutorial_name]['data']
dem_fp = data_d['dem']
finv_fp = data_d['finv']

assert os.path.exists(dem_fp)
assert os.path.exists(finv_fp)
#===============================================================================
# fixtures
#===============================================================================
#===============================================================================
# @pytest.fixture(scope='function')
# @clean_qgis_layer
# def raster_layer(dem_fp):
#     layer = QgsRasterLayer(dem_fp, 'dem_rlay')
#     QgsProject.instance().addMapLayer(layer)
#     return layer
#===============================================================================

# Parameterize with a couple of raster algorithms and their parameters.
@pytest.mark.parametrize("algorithm, params", [
    (
        "qgis:rastersampling",
        { 'COLUMN_PREFIX' : 'SAMPLE_', 
        'INPUT' : finv_fp, 
        'OUTPUT' : 'rastersampling.gpkg', 
        'RASTERCOPY' : dem_fp }
        ),
 
])
def test_processing_environment_run(qgis_processing, tmp_path, algorithm, params, logger):
    """
    Test the ProcessingEnvironment by running a raster algorithm.
    The test uses a sample DEM file and checks that the algorithm produces a valid output.
    """
    #===========================================================================
    # setup
    #===========================================================================
    params['OUTPUT'] = os.path.join(tmp_path, params['OUTPUT'])
    
    #===========================================================================
    # exec
    #===========================================================================
    # Use the ProcessingEnvironment as a context manager.
    with ProcessingEnvironment(logger=logger) as pe:
        # Optionally, you might call pe.xxx_init_algos() here if needed.
        result = pe.run(algorithm, params)
    
    
    #===========================================================================
    # test
    #===========================================================================
    # Validate that the result contains an output key.
    output_key = "OUTPUT"
    assert output_key in result, f"Result does not contain an '{output_key}' key"
    
    output = result[output_key]
    # Check output validity:
    if isinstance(output, str):
        # If a file path is returned, ensure the file exists.
        assert os.path.exists(output), f"Output file {output} was not created"
    elif hasattr(output, "isValid"):
        # If a QGIS layer is returned, check its validity.
        assert output.isValid(), "Output layer is not valid"
    else:
        pytest.fail("Output is neither a file path nor a valid QGIS layer.")
        
        
        
        
        
        
        