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


vfunc_cdf_chk_d = {'tag':str, #parameters expected in crv_d (read from xls tab)
                 'exposure':str,
                 'impact_units':str}