'''
Created on Mar 17, 2025

@author: cef
'''
import os, logging, pprint
import pandas as pd
import pprint, tempfile
import processing
from qgis.core import (
    QgsProcessingContext, QgsProcessingFeedback, QgsFeatureRequest,QgsApplication,
    QgsProject, QgsMapLayer
    )




def get_unique_layer_by_name(layer_name: str, layer_type = None) -> QgsMapLayer:
    """
    Checks if there is a unique layer loaded in the project with the given name,
    optionally filtered by layer type.
    
    Args:
        layer_name (str): The name of the layer to look for.
        layer_type (QgsMapLayer.Type, optional): Filter to consider only layers of a specific type.
    
    Returns:
        QgsMapLayer: The uniquely matching layer, or None if no unique match is found.
    """
    if not layer_name:
        raise ValueError("Layer name must be provided.")
    
    # Retrieve all layers from the current project.
    all_layers_d = QgsProject.instance().mapLayers()
    
    """
    pprint.pprint(all_layers_d)
    """ 
    
    # Filter layers based on name and (if provided) layer type.
    matching_layers = []
    for layer_id, layer in all_layers_d.items():
        if layer.name() == layer_name:
            if layer_type is not None:
                if issubclass(type(layer), layer_type):
                    matching_layers.append(layer)
            else:
                matching_layers.append(layer)
    
    # Return the layer only if there is exactly one match.
    if len(matching_layers) == 1:
        return matching_layers[0]
    
    return None



def vlay_to_df(layer):
    """
    Convert a QgsVectorLayer to a pandas DataFrame.
    
    Parameters:
        layer (QgsVectorLayer): The QGIS vector layer to convert.
        include_geometry (bool): Whether to include the feature geometry (as WKT) in the DataFrame.
        
    Returns:
        pd.DataFrame: A DataFrame containing the layer's attribute data and, optionally, geometry.
    
    Raises:
        ValueError: If the provided layer is not valid.
    """
    

    # Ensure the layer is valid before proceeding.
    if not layer.isValid():
        raise ValueError("The provided QgsVectorLayer is not valid.")

    # Retrieve field names from the layer's fields.
    field_names = [field.name() for field in layer.fields()]
    
 

    # Initialize an empty list to hold feature data.
    features_data = []
    
    # Iterate over each feature in the layer.
    for feature in layer.getFeatures():
        # Map the field names to the feature's attributes.
        row_data = dict(zip([field.name() for field in layer.fields()], feature.attributes()))
        
 

        features_data.append(row_data)

    # Create and return a DataFrame from the list of dictionaries.
    df = pd.DataFrame(features_data, columns=field_names)
    
    
    #check the result is valid
    assert df.shape[0] == layer.featureCount()
    assert df.shape[1] == len(field_names)
    
    return df

#===============================================================================
# PROCESSING--------
#===============================================================================
class ProcessingEnvironment(object):
    def __init__(self, logger=None, context=None, feedback=None,
                 temp_dir=None,
                 ):
        """
        Initialize the processing environment.
        :param logger: a logging.Logger instance.
        :param context: an optional QgsProcessingContext; if None, a new one is created.
        :param feedback: an optional QgsProcessingFeedback; if None, a custom feedback instance is created.
        """
        if logger is None: logger = logging.getLogger(__name__)
        
        self.logger = logger
        if context is None:
            context = QgsProcessingContext()
            context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryAbortOnInvalid)
        self.context = context 
        
        
        self.feedback = feedback if feedback is not None else QgsProcessingFeedback_extended(logger=logger)
        
 

        if temp_dir is None:
            temp_dir = tempfile.mkdtemp()
        os.makedirs(temp_dir, exist_ok=True)
        self.temp_dir = temp_dir

            
        #self.results = []  # Collect results of each processing.run call.
        
        #log all the agos
        #=======================================================================
        # for alg in QgsApplication.processingRegistry().algorithms():
        #     logger.debug("{}:{} --> {}".format(alg.provider().name(), alg.name(), alg.displayName()))
        #=======================================================================
        
    
#===============================================================================
#     def xxx_init_algos(self,
#                     context=None,
#                     invalidGeometry=QgsFeatureRequest.GeometryAbortOnInvalid,
#                         #GeometryNoCheck
#                         #GeometryAbortOnInvalid
#                         
#                     ): #initiilize processing and add providers
#         """
#         crashing without raising an Exception
#         """
#     
#     
#         log = self.logger.getChild('_init_algos')
#         
#         if not isinstance(self.qap, QgsApplication):
#             raise Error('qgis has not been properly initlized yet')
#         
#         #=======================================================================
#         # build default co ntext
#         #=======================================================================
#         """TODO: use users native QGIS environment
#             better consistency between standalone and plugin runs"""
# #===============================================================================
# #         if context is None:
# # 
# #             context=QgsProcessingContext()
# #             context.setInvalidGeometryCheck(invalidGeometry)
# #             
# #         self.context=context
# #===============================================================================
#         
#         #=======================================================================
#         # init p[rocessing]
#         #=======================================================================
#         from processing.core.Processing import Processing
#  
#         Processing.initialize()  
#     
#         QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
#         #QgsApplication.processingRegistry().addProvider(WbtProvider())
#         
#         #=======================================================================
#         # #log all the agos
#         # for alg in QgsApplication.processingRegistry().algorithms():
#         #     log.debug("{}:{} --> {}".format(alg.provider().name(), alg.name(), alg.displayName()))
#         #=======================================================================
#         
#         
#         assert not self.feedback is None, 'instance needs a feedback method for algos to work'
#         
#         log.info('processing initilzied w/ feedback: \'%s\''%(type(self.feedback).__name__))
#         
# 
#         return True
#===============================================================================

    def __enter__(self):
        self.logger.info("Starting processing environment.")
        return self

    def run(self, algorithm, params, logger=None):
        """
        Execute a processing algorithm with the provided parameters.
        :param algorithm: the processing algorithm id.
        :param params: a dictionary of parameters for the algorithm.
        :return: the result dictionary from processing.run.
        """
        #=======================================================================
        # defautls
        #=======================================================================

        assert isinstance(algorithm, str), f"Expected algorithm to be a string, got {type(algorithm)}"
        assert isinstance(params, dict), f"Expected params to be a dict, got {type(params)}"
        
        if logger is None: logger=self.logger
        log=logger.getChild(algorithm)
        
        #=======================================================================
        # run
        #=======================================================================
        log.debug(f"Running algorithm: {algorithm} with parameters: {params}")
        result = processing.run(algorithm, params, 
                                context=self.context, feedback=self.feedback)
        
        #=======================================================================
        # wrap
        #=======================================================================
        #self.results.append(result)
        


        log.info(f"Finished algorithm: {algorithm} w/\n{pprint.pformat(result)}")

        return result

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error(f"Error in processing environment: {exc_val}")
        self.logger.info("Closing processing environment.")
        # Optionally add cleanup code here if necessary.
        return False  # Propagate any exception.

class QgsProcessingFeedback_extended(QgsProcessingFeedback):
    """
    wrapper for easier reporting and extended progress
    
 
    QgsProcessingFeedback inherits QgsFeedback
    """
    
    def __init__(self,
                 logger=None,
                 ):
        
        if logger is None: logger = logging.getLogger(__name__)
        self.logger=logger.getChild('FeedBack')
        
        super().__init__()
                
    def setProgressText(self, text):
        self.logger.debug(text)

    def pushInfo(self, info):
        self.logger.info(info)

    def pushCommandInfo(self, info):
        self.logger.info(info)

    def pushDebugInfo(self, info):
        self.logger.info(info)

    def pushConsoleInfo(self, info):
        self.logger.info(info)

    def reportError(self, error, fatalError=False):
        self.logger.error(error)
        
    
    def upd_prog(self, #advanced progress handling
             prog_raw, #pass None to reset
             method='raw', #whether to append value to the progress
             ): 
            
        #=======================================================================
        # defaults
        #=======================================================================
        #get the current progress
        progress = self.progress() 
    
        #===================================================================
        # prechecks
        #===================================================================
        #make sure we have some slots connected
        """not sure how to do this"""
        
        #=======================================================================
        # reseting
        #=======================================================================
        if prog_raw is None:
            """
            would be nice to reset the progressBar.. .but that would be complicated
            """
            self.setProgress(0)
            return
        
        #=======================================================================
        # setting
        #=======================================================================
        if method=='append':
            prog = min(progress + prog_raw, 100)
        elif method=='raw':
            prog = prog_raw
        elif method == 'portion':
            rem_prog = 100-progress
            prog = progress + rem_prog*(prog_raw/100)
            
        assert prog<=100
        
        #===================================================================
        # emit signaling
        #===================================================================
        self.setProgress(prog)
            
    def setProgress(self, prog):        
        #call QgsFeedback.setProgress
        #this emits 'progressChanged' signal, which would be connected to progressBar.setValue
        # see hlpr.basic.ComWrkr.setup_feedback()
        super().setProgress(float(prog)) 
