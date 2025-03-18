'''
Created on Mar 17, 2025

@author: cef
'''
import pandas as pd



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
