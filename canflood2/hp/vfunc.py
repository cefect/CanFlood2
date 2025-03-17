'''
Created on Mar 11, 2025

@author: cef


helper functions for dealing with CanFlood format 'vfunc' files
'''

import pandas as pd

def load_vfunc_to_df_d(fp):
    return pd.read_excel(fp, sheet_name=None, **{'index_col':None, 'header':None})

def vfunc_df_to_dict(df_raw):
    return df_raw.set_index(0, drop=True).iloc[:, 0].dropna().to_dict()


def vfunc_df_to_meta_and_ddf(df_raw):
    """take a raw page from the vfunc lib and return the meta and dataframes"""
    
    df = df_raw.set_index(0, drop=True).iloc[:, 0].dropna().to_frame()
    
    #get split indexer
    assert 'exposure' in df.index    
    dd_indx = df.index[df.index.get_loc('exposure')+1:] #get those after exposure
    
    
    #get metadata
    meta_d = df.loc[~df.index.isin(dd_indx), :].iloc[:, 0].to_dict()
    del meta_d['exposure']
    
    #get depth-damage dataframe
    """keeping this a dataframe to match CanFlood v1 style
    using generic column labels (vfunc specific lables can be retrieved from the meta_d)
    """
    ddf = df.loc[dd_indx, :].rename(columns={1:'impact'})
    ddf.index.name = 'exposure'
    
    return meta_d, ddf
    
 
    


vfunc_cdf_chk_d = {'tag':str, #parameters expected in crv_d (read from xls tab)
                 'exposure':str,
                 'impact_units':str,
                 'scale_var':str, 'scale_units':str,
                 'exposure_var':str, 'exposure_units':str,
                 'impact_var':str, 'impact_units':str,
                 }