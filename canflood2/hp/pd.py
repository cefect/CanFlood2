'''
Created on Mar 21, 2025

@author: cef
'''

import pandas as pd

def map_multiindex_dtypes(index, dtype_dict):
    """
    Rebuild the MultiIndex of a DataFrame by applying a dtype for each level.

    I'm surprised there is no built-in method for this in pandas.
    """
    

    assert isinstance(index, pd.MultiIndex)

    # Build new arrays for each level of the MultiIndex using the target dtype if provided.
    new_arrays = []
    for level_name in index.names:
        level_values = index.get_level_values(level_name)
        if level_name in dtype_dict:
            # Cast the level's values to the specified dtype.
            new_level = level_values.astype(dtype_dict[level_name])
        else:
            new_level = level_values
        new_arrays.append(new_level)

    # Rebuild the MultiIndex with the same level names.
    result =  pd.MultiIndex.from_arrays(new_arrays, names=index.names)
    
    assert len(result) == len(index), f'failed to rebuild the index properly'
    assert result.dtypes.to_dict() == dtype_dict, f'failed to rebuild the index properly'
    
    return result
 