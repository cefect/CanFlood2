'''
Created on Mar 6, 2025

@author: cef
'''
import os, sys, platform, sqlite3, copy
import pandas as pd
from datetime import datetime

import numpy as np

np.set_printoptions(suppress=True)

from scipy import interpolate, integrate

#===============================================================================
# IMPORTS-----
#===============================================================================

from .hp.basic import view_web_df as view
from .hp.assertions import assert_index_match
from .hp.sql import get_table_names, pd_dtype_to_sqlite_type
from . import __version__


from .db_tools import (get_template_df, assert_df_template_match)

from .assertions import (
    assert_projDB_fp, assert_hazDB_fp, assert_df_matches_projDB_schema, assert_projDB_conn,
    assert_series_match
    )
from .parameters import (
    projDB_schema_modelTables_d, project_db_schema_d,  modelTable_params_d
    )

import canflood2.parameters as parameters


import scipy.integrate as integrate

# Select the appropriate integration function based on the user's SciPy version.
if hasattr(integrate, 'trapezoid'):
    integration_func = integrate.trapezoid
else:
    integration_func = integrate.trapz

#===============================================================================
# PARAMS--------
#===============================================================================


modelTable_params_allowed_d = copy.copy(modelTable_params_d['table_parameters']['allowed']) 
#===============================================================================
# CLASSES--------
#===============================================================================


class ModelNotReadyError(Exception):
    """Exception raised when the model is not ready to run."""
 


class Model_run_methods(object):
    """organizer for the model run methods"""
    
    def run_model(self,
                  projDB_fp=None,
                  progressBar=None,
                  logger=None,
                  ):
        """run the model"""
 
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('run_model')
        start_time= datetime.now()        
 
                
        def add_to_prog(increment):
            """helper for adding to the progress bar"""
            if progressBar is not None:
                current_value = progressBar.value()
                if current_value<100:
                    progressBar.setValue(current_value + increment)
                
        add_to_prog(5)
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
            
        
 
        

            
            
        #=======================================================================
        # prechecks
        #=======================================================================
        self.assert_is_ready(logger=log)
        
        assert_projDB_fp(projDB_fp, check_consistency=True)
        log.info(f'running model from {os.path.basename(projDB_fp)}')
        
        """too tricky to work witha  single connection
        most things are setup to work of the filepath
        with sqlite3.connect(projDB_fp) as conn: 
        
            assert_projDB_conn(conn, check_consistency=True)
        """
        add_to_prog(5)
        #=======================================================================
        # run sequence
        #=======================================================================
        skwargs = dict(projDB_fp=projDB_fp, logger=log)
        
        #compute damages 
        self._table_impacts_to_db(**skwargs)
        add_to_prog(10)
        
        #simplify and add EAD to clumns
        self._table_impacts_prob_to_db(**skwargs)
        add_to_prog(10)
        
        #row-wise EAD
        self._table_ead_to_db(**skwargs)
        add_to_prog(10)
        
        #model-wide EAD
        result = self._set_ead_total(**skwargs)
        add_to_prog(10)
        
 
        
        log.info(f'finished running model  in {datetime.now()-start_time} w/ EAD={result}')
        
        return result
        
    def _table_impacts_to_db(self, projDB_fp=None, logger=None, precision=3):
        """compute the damages and write to the database"""
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('_table_impacts_to_db')
        
        #=======================================================================
        # load data-------
        #=======================================================================
        #=======================================================================
        # #model exposure and inventory
        #=======================================================================
 
        expos_df, finv_dx = self.get_tables(['table_expos', 'table_finv'], projDB_fp=projDB_fp)
        
        #clean up indexers
        expos_df.columns.name = 'event_names'
        
        assert_finv_match = lambda x: self.assert_finv_index_match(x, finv_index=finv_dx.index)
        
        assert_finv_match(expos_df.index)
        #assert set(finv_dx.index.unique('indexField')) == set(expos_df.index), 'index mismatch'
        
        
                
        #=======================================================================
        # #DEM
        #=======================================================================
        if self.param_d['finv_elevType']=='ground':
            dem_df = self.get_tables(['table_gels'], projDB_fp=projDB_fp)[0]
            assert_finv_match(dem_df.index)
 
        else:
            dem_df = None
        
        #=======================================================================
        # #dfuncs
        #=======================================================================
        if not 'L2' in self.param_d['expo_level']:
            raise NotImplementedError(f'expo_level=\'{self.param_d["expo_level"]}\'')
 
        vfunc_index_df, vfunc_data_df = self.parent.projDB_get_tables(['06_vfunc_index', '07_vfunc_data'], projDB_fp=projDB_fp)
        
        assert set(finv_dx['tag']).issubset(vfunc_index_df.index), 'missing tags'
        
 
        #=======================================================================
        # compute-------
        #=======================================================================
        #loop on each tag (unique damage function)
        result_d = dict()
        g_vfunc = vfunc_data_df.round(precision).groupby('tag')
        g = finv_dx.groupby('tag')
        log.info(f'computing damages for {len(g)} ftags')
        for i, (tag, gdf) in enumerate(g):
            log.debug(f'computing damages for {i+1}/{len(g)} tag=\'{tag}\' w/ {len(gdf)} assets')
            
 
            #===================================================================
            # prep exposures----------
            #===================================================================
            #get these depths
            expoi_df = expos_df.loc[expos_df.index.isin(gdf.index.unique('indexField')), :]
 


            
            #===================================================================
            # #adjust for DEM
            #===================================================================
            if dem_df is None:
                deps_df = expoi_df
            else:
                #get the DEM values
                gels_s = dem_df.loc[dem_df.index.isin(gdf.index.unique('indexField')), :].iloc[:, 0]                
                
                #subtract the DEM from the WSE
                deps_df = expoi_df.subtract(gels_s, axis=0)
                
            #===================================================================
            # #adjust for asset height (elv)            
            #===================================================================
            #join the exposures onto the assets
            dep_elev_df = gdf['elev'].to_frame().join(deps_df, on='indexField')
            
            #subrtact the elev column from the other columns
            deps_df = dep_elev_df.drop(columns='elev').subtract(dep_elev_df['elev'], axis=0)
            deps_df.columns.name = 'event_names'

            negative_bx = deps_df<0
            if negative_bx.any().any():
                log.warning(f'got {negative_bx.sum().sum()}/{deps_df.size} negative depths for tag \'{tag}\'')
            #===================================================================
            # final prep
            #===================================================================
            #stack into a series
            deps_s = deps_df.round(precision).stack().rename('exposure')
 
            #get unique
            deps_ar = np.unique(deps_s.dropna().values) #not sorting

 
            #===================================================================
            # prep dfunc----------
            #===================================================================
            dd_ar = g_vfunc.get_group(tag).sort_values('exposure').loc[:, ['exposure', 'impact']].astype(float).T.values
            
            #check monotonocity
            assert np.all(np.diff(dd_ar[0])>0), 'exposure values must be increasing' #redundant with sort_values?
            assert np.all(np.diff(dd_ar[1])>=0), 'impact values must be non-decreasing'
            
            #===================================================================
            # compute damages
            #===================================================================
            #===================================================================
            # get_dmg = lambda depth: np.interp(depth, #depth find damage on
            #                                 dd_ar[0], #depths (xcoords)
            #                                 dd_ar[1], #damages (ycoords)
            #                                 left=0, #depth below range
            #                                 right=max(dd_ar[1]), #depth above range
            #                                 )
            # get_dmg(deps_ar)
            # e_impacts_d = {dep:get_dmg(dep) for dep in deps_ar}
            #===================================================================
            expo_ar = np.interp(deps_ar, #depth find damage on
                    dd_ar[0], #depths (xcoords)
                    dd_ar[1], #damages (ycoords)
                    left=0, #depth below range
                    right=max(dd_ar[1]), #depth above range
                    )
            
            """
            plot_line_from_array(dd_ar, deps_ar)
            """
            
            #join back onto the depths
            result_dx = deps_s.to_frame().join(pd.Series(expo_ar, index=deps_ar, name='impact'), on='exposure')
            

                
            
                
            
            #===================================================================
            # scale
            #===================================================================
            #apply the scale
            dx = result_dx.join(gdf['scale'], on=gdf.index.names).drop('exposure', axis=1)
            result_dx['impact_scaled'] = dx['impact']*dx['scale']
            
            #===================================================================
            # cap
            #===================================================================
            dx = result_dx.join(gdf['cap'], on=gdf.index.names).loc[:, ['impact_scaled', 'cap']]
            result_dx['impact_capped'] = dx.min(axis=1)
            
            #===================================================================
            # #add any missing entries that were all null
            #===================================================================
            if result_dx.isna().any().any():
                raise NotImplementedError('no support for missing entries yet')
 
            
            # Create a new MultiIndex from the product of the existing index and the new level values
            complete_index = pd.MultiIndex.from_product(
                [
                    gdf.index.get_level_values(0).unique(),
                    gdf.index.get_level_values(1).unique(),
                    expos_df.columns
                ],
                names=gdf.index.names + [expos_df.columns.name]
            )
            
 
            bx = complete_index.isin(result_dx.index)

            
            if not bx.all():
                log.debug(f'adding {np.invert(bx).sum()}/{len(bx)} missing entries for tag \'{tag}\'')
                
                assert expoi_df.isna().any().any() 
                
                #add the missing indexers as nans to the result
                result_dx = result_dx.reindex(complete_index)
            
            #===================================================================
            # wrap
            #===================================================================
            log.debug(f'finished computing damages for tag \'{tag}\' w/ {len(result_dx)} records')
            result_d[tag] = result_dx
            
        #=======================================================================
        # collectg
        #=======================================================================
        mresult_dx = pd.concat(result_d, names=['tag'])#.reorder_levels(['indexField', 'nestID', 'tag', 'event_names']).sort_index()
        
        # Check if the 'tag' level is redundant against all other indexers
        assert mresult_dx.index.droplevel('tag').nunique() == mresult_dx.index.nunique(), "The 'tag' level is not redundant"
 
        # Drop the 'tag' level from the index
        mresult_dx = mresult_dx.droplevel('tag').reorder_levels(['indexField', 'nestID', 'event_names']).sort_index()
 
        #=======================================================================
        # #check
        #=======================================================================

        
        #check the index matches the finv_dx
        
        mresult_dx_index_check = mresult_dx.index.droplevel('event_names').drop_duplicates().sort_values()
        assert_finv_match(mresult_dx_index_check)
        #assert mresult_dx_index_check.equals(finv_dx.index.sort_values()), 'Index mismatch'

        log.info(f'finished computing damages w/ {mresult_dx.shape}')
        
        #=======================================================================
        # write to projDB
        #=======================================================================
        """
        mresult_dx.index.dtypes
        """
        self.set_tables({'table_impacts':mresult_dx}, projDB_fp=projDB_fp)
 
        
        return mresult_dx
    """
    mresult_dx.dtypes
    """
    
    def _table_impacts_prob_to_db(self, projDB_fp=None, logger=None):
        """compute and set the simple impacts table
        
        this is a condensed and imputed version of the impacts table
        decided to make this separate as users will expect something like this
            but we want to maintain the compelte table for easier backend calcs
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('_table_impacts_prob_to_db')
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
            
        log.debug(f'computing and writing simple impacts from \n    {projDB_fp}')
        
        #=======================================================================
        # load data
        #=======================================================================
        impacts_dx = self.get_tables(['table_impacts'], projDB_fp=projDB_fp)[0]
        
        log.debug(f'loaded impacts w/ {impacts_dx.shape}')
        
        #=======================================================================
        # simplifyt
        #=======================================================================
        
        #sum on nestID and retrieve impacts
        df = impacts_dx['impact_capped'].groupby(['indexField', 'event_names']).sum().unstack('event_names').fillna(0.0)
        
        
        #=======================================================================
        # #remap columns to ARI----
        #=======================================================================
        #=======================================================================
        # haz events
        #=======================================================================
        haz_events_df = self.parent.projDB_get_tables(['05_haz_events'], projDB_fp=projDB_fp)[0]
        
        haz_events_s = haz_events_df.set_index('event_name')['prob']
        
        #get probability type    
        haz_meta_s = self.parent.projDB_get_tables(['04_haz_meta'], projDB_fp=projDB_fp)[0].set_index('varName')['value']
        
        if haz_meta_s['probability_type']=='0':
            probability_type = 'AEP'
        elif haz_meta_s['probability_type']=='1':
            probability_type = 'ARI'
        else:
            raise KeyError(f'bad probability_type: {haz_meta_s["probability_type"]}')
 

        log.debug(f'retrieved {len(haz_events_s)} events w/ probability_type=\'{probability_type}\'')
        
        #convert to AEP
        if probability_type=='AEP':
            pass
        else:
            haz_events_s = 1/haz_events_s
            
        haz_events_s = haz_events_s.rename('AEP')
        
        #=======================================================================
        # remap
        #=======================================================================
        #by convention, the x-axis is AEP (leftward = rare; rightward=common)
        impacts_prob_df = df.rename(columns=haz_events_s).sort_index(ascending=True, axis=1)
        impacts_prob_df.columns.name = haz_events_s.name
        
        #=======================================================================
        # check
        #=======================================================================
        
        self.assert_impacts_prob_df(impacts_prob_df)
        
        #=======================================================================
        # write
        #=======================================================================
        self.set_tables({'table_impacts_prob':impacts_prob_df}, projDB_fp=projDB_fp)
        
 
        
        
    
    def _table_ead_to_db(self, projDB_fp=None, logger=None,

                         
                         ):
        """compute the row-wise EAD from the damages and write to the database
        
        see CanFloodv1: riskcom.RiskModel.calc_ead()
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('_table_ead_to_db')
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
        
        log.debug(f'computing EAD from \n    {projDB_fp}')
        #=======================================================================
        # load and prep data and params-------
        #=======================================================================
        #=======================================================================
        # damages
        #=======================================================================
        impacts_df_raw = self.get_tables(['table_impacts_prob'], projDB_fp=projDB_fp)[0]
        impacts_df_raw.columns = impacts_df_raw.columns.astype(float).rename('AEP')

        self.assert_impacts_prob_df(impacts_df_raw)
        

        #=======================================================================
        # compute-------
        #=======================================================================

        """
        impacts_prob_df.columns
        view(dmgs_dx)
        """
        #=======================================================================
        # add synthetic events/tails
        #=======================================================================
        """for asset-wise, we use a simple left/lowP = flat syntethic event
            other parmaters dont really  make sense per-asset
        
        fancyier tails are applied in model-wise _set_ead_total()
        """
        impacts_df = impacts_df_raw.copy()
        impacts_df[0.0] = impacts_df.iloc[:, 0]
        impacts_df = impacts_df.sort_index(ascending=True, axis=1)
        
        self.assert_impacts_prob_df(impacts_df)
        
        log.debug(f'added synthetic event for 0.0 AEP')
        #=======================================================================
        # calc areas
        #=======================================================================
        log.debug(f'computing areas for {impacts_df.shape}')
        ead_df = impacts_df.apply(get_area_from_ser, axis=1).rename('ead').to_frame()

        #=======================================================================
        # calc EAD
        #=======================================================================
        """
        see CanFloodv1: riskcom.RiskModel._get_ev()
        """
            
        
        #=======================================================================
        # write to projDB
        #=======================================================================
 
        self.set_tables({'table_ead':ead_df}, projDB_fp=projDB_fp)
        
        return ead_df
    
    def _set_ead_total(self, projDB_fp=None, logger=None,
                       ead_lowPtail=None, ead_highPtail=None,
                         ead_lowPtail_user=None, ead_highPtail_user=None,
                         ):
        """compute the model-wide EAD with fancy tails
        
        NOTE: we don't use the row-wise EAD as we want to fancier tails
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('_set_ead_total')
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
            
            
        #=======================================================================
        # damages
        #=======================================================================
        impacts_df = self.get_tables(['table_impacts_prob'], projDB_fp=projDB_fp)[0]
        impacts_df.columns = impacts_df.columns.astype(float).rename('AEP')

        self.assert_impacts_prob_df(impacts_df)
        
        log.debug(f'loaded impacts w/ {impacts_df.shape}')
        #=======================================================================
        # risk params
        #=======================================================================
        #get the params
        param_s = self.get_table_parameters(projDB_fp=projDB_fp).set_index('varName')['value']
        
        if ead_lowPtail is None:
            ead_lowPtail = param_s['ead_lowPtail']
        if ead_highPtail is None:
            ead_highPtail = param_s['ead_highPtail']
 
        
        #check
        assert ead_lowPtail in modelTable_params_allowed_d['ead_lowPtail'], f'bad ead_lowPtail: {ead_lowPtail}'
        assert ead_highPtail in modelTable_params_allowed_d['ead_highPtail'], f'bad ead_highPtail: {ead_highPtail}'
        
        if 'user' in ead_lowPtail:
            if ead_lowPtail_user is None:
                ead_lowPtail_user = float(param_s['ead_lowPtail_user'])
 
        if 'user' in ead_highPtail:
            if ead_highPtail_user is None:
                ead_highPtail_user = float(param_s['ead_highPtail_user'])
            
        log.debug(f'loaded risk params ead_lowPtail=\'{ead_lowPtail}\' ead_highPtail=\'{ead_highPtail}\'')
        
        
        #=======================================================================
        # get totals--------
        #=======================================================================
        impacts_s = impacts_df.sum(axis=0).rename('impacts')
        
        #check conformance (but not index)
        check_impacts = lambda x: self.assert_impacts_prob_df(
            x.to_frame().T.reset_index(drop=True).rename_axis(index='indexField'),
            check_finv=False)
        #=======================================================================
        # add tails--------
        #=======================================================================
 
        #=======================================================================
        # add low probability tail (leftward)
        #=======================================================================
        if ead_lowPtail=='none':
            pass
        elif ead_lowPtail=='flat':
            impacts_s[0.0] = impacts_s.iloc[0]
 
        elif ead_lowPtail=='extrapolate':
            #leftward extrapolation to get y value at x=0 
            # Select the two smallest AEP values
            x0, x1 = impacts_s.index.values[0:2]
            
            # Vectorized linear extrapolation: compute y(0) for every row. 
            impacts_s[0.0] =  impacts_s[x0] + (0 - x0) * (impacts_s[x1] - impacts_s[x0]) / (x1 - x0)            
 
        elif 'user' in ead_lowPtail:
            assert ead_lowPtail_user>impacts_s.max(), f'specifeid lowPtail must be greater than the maximum impact value {impacts_s.max()}'
            impacts_s[0.0] = ead_lowPtail_user
        else:
            raise KeyError(f'unreecognized ead_lowPtail: {ead_lowPtail}')
        
 
        impacts_s = impacts_s.sort_index(ascending=True)
        
        #check it
        check_impacts(impacts_s)
        
        #=======================================================================
        # high probability (rightward)
        #=======================================================================
        
        if ead_highPtail=='none':
            pass
        elif ead_highPtail=='extrapolate':
            #rightward extrapolation to get x value at y=0            
            x0, x1 = impacts_s.index.values[-2:]
            
            p_for_ead0 = x0 - (impacts_s[x0] * (x1 - x0)) / (impacts_s[x1] - impacts_s[x0])
            
            impacts_s[p_for_ead0] = 0.0
 
        elif 'user' in ead_highPtail:
            assert ead_highPtail_user>np.max(impacts_s.index), (
                f'specifeid highPtail must be greater than the maximum AEP value {impacts_s.index.max()}')
            impacts_s[ead_highPtail_user] = 0.0
        else:
            raise KeyError(f'unreecognized ead_highPtail: {ead_highPtail}')
        
        
        impacts_s = impacts_s.sort_index(ascending=True)
        
        #check it
        check_impacts(impacts_s)
        """
        import matplotlib.pyplot as plt
        plt.show()
        impacts_s.plot(marker='o', markersize=5, markerfacecolor='b')
        """
        
        log.debug(f'added tails to impacts \n{impacts_s}')
        #=======================================================================
        # integrate-----
        #=======================================================================
        result_ead = get_area_from_ser(impacts_s)
        
        #=======================================================================
        # wrap-------
        #=======================================================================
        #=======================================================================
        # set table
        #=======================================================================
        df = impacts_s.to_frame().reset_index()
        #df.dtypes
        self.set_tables({'table_impacts_sum':df}, projDB_fp=projDB_fp)
        
        #=======================================================================
        # set parameter value
        #=======================================================================
        self.set_parameter_value('result_ead', result_ead, projDB_fp=projDB_fp)
        
        
        log.info(f'finished computing EAD w/ {result_ead}')
        
        return result_ead
        
class Model_table_assertions(object):
    """organizer for the model table assertions"""
    def assert_finv_index_match(self, index_test, finv_index = None, projDB_fp=None):
        """check that the finv index matches the project database
        
        flexible to check index w/ or w/o nestID
        """
        #=======================================================================
        # defaults
        #=======================================================================
 
 
 
        #=======================================================================
        # load data
        #=======================================================================
        if finv_index is None:
            finv_index = self.get_tables(['table_finv'], projDB_fp=projDB_fp)[0].index
 
        if not isinstance(finv_index, pd.MultiIndex):
            raise AssertionError(f'bad type on the finv_index:{type(finv_index)}')
        
        #=======================================================================
        # check
        #=======================================================================
        try:
            if isinstance(index_test, pd.MultiIndex):
                if not index_test.names == ['indexField', 'nestID']:
                    raise AssertionError(f'bad index_test names: {index_test.names}')
                assert_index_match(index_test, finv_index)
                
            elif isinstance(index_test, pd.Index):
                assert index_test.name == 'indexField'
                assert_index_match(index_test, finv_index.get_level_values('indexField'))
                
            else:
                raise IOError(f'bad index_test type: {type(index_test)}')
            
        except Exception as e:
            raise AssertionError(f'index {index_test.shape} does not match finv index \n    {e}') from None
        
        
 
        
        return
    
    def assert_impacts_prob_df(self, impacts_prob_df=None, projDB_fp=None, check_finv=True):
        """check the impacts simple table conform to expectations
        
        using risk-curve convention for column order:
            leftward = low prob; rightward=higher prob
            
        CanFlood v1 had the opposite?
        
        
        
        """
        if impacts_prob_df is None:
            impacts_prob_df = self.get_tables(['table_impacts_prob'], projDB_fp=projDB_fp)[0]
        
        #=======================================================================
        # #simple schema check
        #=======================================================================
        schema_df = get_template_df('table_impacts_prob', template_prefix=self.template_prefix_str)
        assert_df_template_match(impacts_prob_df, schema_df, check_dtypes=False)
 
        assert impacts_prob_df.columns.name =='AEP'
        assert 'float' in impacts_prob_df.columns.dtype.name
        #=======================================================================
        # index check
        #=======================================================================
        if check_finv:
            self.assert_finv_index_match(impacts_prob_df.index, projDB_fp=projDB_fp)
        

        #=======================================================================
        # check order
        #=======================================================================
        #v1 had a different convention?
        if not np.all(np.diff(impacts_prob_df.columns) >= 0):
            raise AssertionError('passed headers are not ascending')
        
        #=======================================================================
        # check everything is positive
        #=======================================================================
        booldf = impacts_prob_df >= 0
        if not booldf.all().all():
            raise AssertionError('Negative values found in table_impacts_prob')
        
        #=======================================================================
        # check for damage monotonicity
        #=======================================================================
        if not np.all(impacts_prob_df.diff(axis=1).dropna(axis=1)<=0):
            raise AssertionError('damage values are not monotonically decreasing')
 

 
    
class Model(Model_run_methods, Model_table_assertions):
    """skinny helper functions for dealing with an individual model 
    on the model suite tab
    
    
    went back and forth on this
        seems a slightly more convenient to instance a small class like this for each model
        needs to be very lightweight though
        and needs to be properly closed
        all configuration and running should be handled by the Model_config_dialog 
            which is instanced once
    """
    
    
    """ 

    """
    status = 'initialized'
    asset_label=''
    consq_label=''
    
    #reference to the model config dialog
    #detaches on Model_config_dialog._custom_cleanup()
    Model_config_dialog=None 
    
    widget_d=None #container for Main_dialog's run, fongi, minus, plus buttons on teh model suite tab
    
    #result_ead=None
    param_d=None
    
    compile_model_tables = [k for k,v in modelTable_params_d.items() if v['phase']=='compile'] 
    
 
    
    def __init__(self,                  
                 parent=None, 
                 #widget_suite=None, 
                  
                 category_code='c1', 
                 modelid=0, logger=None,
                 ):
 
        self.parent=parent #Main_dialog
        self.category_code = category_code
        self.modelid = int(modelid)
        self.name = f'{category_code}_{modelid}'
        self.logger = logger.getChild(self.name)
        self.template_prefix_str = f'model_{self.name}_'
 
        
        self.logger.debug(f'initialized')
        
    def get_index_d(self):
        return {'category_code':self.category_code, 'modelid':self.modelid, 
                #'category_desc':self.category_desc,
                'name':self.name,
                #'status':self.status,
                }
        
    def get_model_index_ser(self,
                            param_df=None,
                             **kwargs):
        """get row from model index for this model
        
        we assume the UI has been written to hte projDB
        """
        #model_index_dx = self.parent.get_model_index_dx()
        modelid = self.modelid
        category_code = self.category_code
        
 
        #=======================================================================
        # from parameters import table
        #=======================================================================
        if param_df is None:
            param_df = self.get_table_parameters()
            
        try:
            s = param_df[param_df['model_index']].set_index('varName')['value']
        except Exception as e:
            raise IOError(f'failed to get model index data from parameters table\n    {e}')
        
        
        #=======================================================================
        # table names
        #=======================================================================
        table_names_d = {k:np.nan for k in projDB_schema_modelTables_d.keys()}
        table_names_d.update(self.get_table_names_all(result_as_dict=True))
        
        s = pd.concat([s, pd.Series(table_names_d)], axis=0) 
        
        #=======================================================================
        # results
        #=======================================================================
        """included in the params now
        s['result_ead'] = self.result_ead if self.result_ead is not None else np.nan
        """

 
        
        #=======================================================================
        # post
        #=======================================================================
 
        s.name=(category_code, modelid) #rename for multindex
        assert not None in s.values
        assert not 'nan' in s.values
        return s
        

 

    def get_table_names(self, table_names, result_as_dict=False):
        """Return the matching table names for this model."""
        assert isinstance(table_names, list)
        template_names = projDB_schema_modelTables_d.keys()
        for tn in table_names:
            assert tn in template_names, f'bad table name: {tn}'
    
        result = list(self.template_prefix_str + f'{k}' for k in table_names)
        
        if result_as_dict:
            return dict(zip(table_names, result))
        else:
            return result
        
 

 
 

    def get_table_names_all(self, projDB_fp=None, result_as_dict=False):
        """Return all available matching table names."""
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
    
        with sqlite3.connect(projDB_fp) as conn:
            table_names = get_table_names(conn)
            match_l = [k for k in table_names if f'model_{self.name}' in k]
    
        if result_as_dict:
            return {k.replace(self.template_prefix_str, ''): k for k in match_l}
        else:
            return match_l

    
    def get_tables(self,table_names_l, result_as_dict=False, **kwargs):
        """load model specific tables from generic table names"""
        assert isinstance(table_names_l, list), type(table_names_l)
        names_d = self.get_table_names(table_names_l, result_as_dict=True)
        
        full_names = list(names_d.values())             
        
                
        tables =  self.parent.projDB_get_tables(full_names,template_prefix=self.template_prefix_str, **kwargs)
        
        if result_as_dict:
            return dict(zip(table_names_l, tables))
        else:
            return tables
        
    
    def get_table_parameters(self, **kwargs):
        """special loader for the parameters"""
        df_raw = self.get_tables(['table_parameters'], **kwargs)[0]
        
        return format_table_parameters(df_raw)
    
 
    

    
    
    def get_model_tables_all(self, projDB_fp=None, result_as_dict=True):
        """load all tables for this model"""
        table_names_d = self.get_table_names_all(projDB_fp=projDB_fp, result_as_dict=True)
        
        #=======================================================================
        # some tables
        #=======================================================================
        if len(table_names_d)>0:
        
            tables_l = self.parent.projDB_get_tables(list(table_names_d.values()), 
                                                     projDB_fp=projDB_fp, 
                                                     result_as_dict=False,
                                                     template_prefix=self.template_prefix_str,
                                                     )
            
            if len(table_names_d)==1:
                tables_l = [tables_l]
            
            if result_as_dict:
                return dict(zip(table_names_d.keys(), tables_l))
            else:
                return tables_l
        
        #=======================================================================
        # no tables
        #=======================================================================
        else:
            if result_as_dict:
                return dict()
            else:
                return None
        
        
        
 
        return 
        
 

    
    def set_tables(self, df_d, **kwargs):
        """write the tables to the project database"""
        
        #recase the names

        # Get the table names
        table_names = self.get_table_names(list(df_d.keys()))       
 
        
        # Recast the DataFrame dictionary with the correct table names
        df_d_recast = dict(zip(table_names, df_d.values()))
        
        # Write the tables to the project database
        result =  self.parent.projDB_set_tables(df_d_recast, template_prefix=self.template_prefix_str, **kwargs)
        
        #=======================================================================
        # #handle updates
        #=======================================================================
        names_d = dict(zip(df_d.keys(), table_names ))
        for template_name, full_name in names_d.items():
            if template_name=='table_parameters':
                self.parent.update_model_index_dx(self)
                self.update_parameter_d()
                
            #add the table name to the parameters
            elif template_name in projDB_schema_modelTables_d.keys():
                self.set_parameter_value(template_name, full_name)
 
            else:
                raise IOError(f'unknown table name: {template_name}')
 
 
        self.compute_status() 
        return result
    
    def get_parameter_value(self, varName, projDB_fp=None):
        """wrapper to get a single project parameter value
        
        could set the parameters as a dictionary for faster retrival
            but then we need to worry about updating....
        """
        param_df = self.get_table_parameters(projDB_fp=projDB_fp)
        return param_df.loc[param_df['varName']==varName, 'value'].values[0]
    
    def set_parameter_value(self, varName, value, projDB_fp=None):
        """wrapper to set a single project parameter value"""
        param_df = self.get_table_parameters(projDB_fp=projDB_fp)
        param_df.loc[param_df['varName']==varName, 'value'] = value
        
        self.set_tables({'table_parameters':param_df}, projDB_fp=projDB_fp)
        
    def update_parameter_d(self, **kwargs):
        """set the parameters as a dictionary for faster retrival
        
        omitting blanks from container
        """
        df = self.get_table_parameters(**kwargs)
        """
        view(df)
        """
        self.param_d = df.set_index('varName')['value'].dropna().to_dict()
        
    
    
    

    def _get_status(self, param_df=None):
        """determine the status of the model
        
        
        
        
        status values
            initialized - value before _get_status is called
            incomplete – Implies the template is still in an unfinished, configurable state.
            ready – all ui components completed
            failed – Clearly denotes that a model run has encountered an error.
            complete – Conveys that the model run has finished successfully.
            
        """
        if param_df is None:
            #load the model parameter table from the projDB
            #WARNING: this may be coming from some test pickle
            param_df = self.get_table_parameters() 
            
            
        self.update_parameter_d()
            
        status=None
        msg=None
        #=======================================================================
        # parameters
        #=======================================================================
        #check if all of the required parameters are populated
        param_df_required = param_df.loc[param_df['required']].loc[:, ['varName', 'value']]  
        bx = param_df_required['value'].isna()
        
        if bx.any():
            status = 'incomplete'
            
            msg = f'missing required parameters: \n    {param_df_required.loc[bx, "varName"].tolist()}'
 
            
            
        else:
            """performing checks in sequence for some redundancy
            i.e., not simply checking if the result is present"""
            
            #===================================================================
            # vfunc
            #===================================================================
            
            
            #===================================================================
            # tables
            #===================================================================
            df_d = self.get_model_tables_all(result_as_dict=True)
            
            #check missing tables
                       
            miss_l = set(self.compile_model_tables) - set(df_d.keys())
            
            if len(miss_l)>0:
                status = 'incomplete'
                msg = f'missing tables:\n    {miss_l}'
            else:
                
                #tables populated
                for table_name in self.compile_model_tables:
                    
                    if df_d[table_name].shape[0]==0:
                        status = 'incomplete'
                        msg = f'empty table: {table_name}'
                        break
                    
                #===============================================================
                # ready vs. complete
                #===============================================================
                if status is None:
                    msg=None #clear from above            
     
                    #check if results have been computed
                    if 'result_ead' in self.param_d:
                        if pd.isnull(self.param_d['result_ead']):
                            status = 'ready'
                        else:
                            status = 'complete'     
                    else:
                        status = 'ready'
 
            
        assert not status is None, 'failed to determine status'
        return status, msg

    def compute_status(self, logger=None):
        """load info from the projDB and use to determine status
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None:logger = self.logger
        log = logger.getChild('compute_status')
 
        
        #=======================================================================
        # get status
        #=======================================================================
        status, msg = self._get_status()
            
        log.debug(f'status={status}\n    {msg}')
            
            
        #=======================================================================
        # update
        #=======================================================================
        #update the table_parameters and the model_index
        #self.set_parameter_value('status', status)
        
        #self.update_parameter_d()
        
        #update the main dialog
        try:
            self.widget_d['label_mod_status']['widget'].setText(status)
        except Exception as e:
            raise IOError(f'failed to update Main_dialog status label w/ \n    {e}')
        
        #update model config dialog
        if not self.Model_config_dialog is None:
            try:
                self.Model_config_dialog.label_mod_status.setText(status)
            except Exception as e:
                raise IOError(f'failed to update Model_config_dialog status label w/ \n    {e}')
        
            
        
            
        self.status = status
        
        return status
        
        
    def assert_is_ready(self, logger=None):
        """check if the model is ready to and provide a verbose output if not"""
        if logger is None: logger = self.logger
        log = logger.getChild('assert_is_ready')
        #=======================================================================
        # load data
        #=======================================================================
 
        param_df = self.get_table_parameters()
        
        status, msg = self._get_status(param_df=param_df)
        log.debug(f'status=\'{status}\'')
        
        #=======================================================================
        # report on non-ready status
        #=======================================================================
        if not status in ['ready', 'complete']:            
            raise ModelNotReadyError(f'model is not ready\n    {msg}')
 
        log.debug(f'model is ready`')
 

        return #no need to resturn anything
 
            


        
        
    def __exit__(self, exc_type, exc_value, traceback):
        """Cleanup resources when exiting the context or explicitly calling cleanup."""
        if self.logger:
            self.logger.debug(f'Exiting and destroying {self.name}')
        
 
        
        # Break any remaining circular references or held pointers:
        self.parent = None
        self.logger = None
        # You can delete attributes if needed:
        # for attr in list(self.__dict__.keys()):
        #     delattr(self, attr)
        
        # Returning False lets any exception propagate, which is standard
        return False
        
#===============================================================================
# common functions-------------------
#===============================================================================
#===============================================================================
# def df_to_sql_templated(df, table_name, conn, **kwargs):
#     """wrapper for writing a panads dataframe to a sqlite table  using the types from the template"""
#     dtype=None
#     if table_name in project_db_schema_d:
#         template_df = project_db_schema_d[table_name]
#         if not template_df is None:
#             template_df.dtypes
#===============================================================================




def get_area_from_ser(ser, dx=0.1):
    """
    Compute the area under the curve defined by a pandas Series,
    where the x-values are taken from the Series index (assumed numeric)
    and the y-values are the Series' values.
    
    Uses the appropriate integration function from SciPy as determined at import.
    
    Parameters:
        ser (pd.Series): Series with numeric index (x-values) and values (y-values).
        dx (float): Optional spacing parameter (ignored if x is provided).
    
    Returns:
        float: Computed area under the curve.
    """
    try:
        x = ser.index.astype(float)
    except ValueError as e:
        raise ValueError("Series index could not be converted to float. Ensure your column names are numeric.") from e

    y = ser.values
    return integration_func(y, x=x, dx=dx)
    

def format_table_parameters(df_raw):
    return df_raw.copy().astype({'required':bool, 'model_index':bool}).fillna(np.nan)

def _get_proj_meta_d(log, 
 
                   ):
    """database metadata for tracking progress of db edits
    
 
    """
    
    d = {
 
            'script_name':[os.path.basename(__file__)],
            'script_path':[os.path.dirname(__file__)],
            'now':[datetime.now()], 
            'username':[os.getlogin()], 

            'canflood2_version':[__version__], 
            'python_version':[sys.version.split()[0]],
            'platform':f"{platform.system()} {platform.release()}"            
            
            }
    #add qgis
    try:
        from qgis.core import Qgis
        d['qgis_version'] = Qgis.QGIS_VERSION
    except Exception as e:
        log.warning(f'failed to retrieve QGIS version\n    {e}')
        
 
    return d

def xxx_update_proj_meta(log, conn, meta_d=dict()):
    
    #retrieve data
    d = _get_proj_meta_d(log)
    d.update(meta_d) #overwrite/update
    
    #push to database
    proj_meta_df = pd.DataFrame(d)
    df_to_sql(proj_meta_df, 'project_meta', conn, if_exists='append')
 
    log.debug(f'updated \'project_meta\' w/ {proj_meta_df.shape}')
    return proj_meta_df



 


def plot_line_from_array(dd_ar, depths=None):
    """
    Plots a line from a 2 x N numpy array and optionally plots depths as black circles.

    Parameters:
        dd_ar (np.ndarray): A 2 x N array where the first row contains x-values
                            and the second row contains y-values.
        depths (np.ndarray, optional): A 1 x N array containing x-values for depths.
    """
    import matplotlib.pyplot as plt
    if dd_ar.shape[0] != 2:
        raise ValueError("The input array must have exactly 2 rows.")

    x = dd_ar[0]
    y = dd_ar[1]

    plt.figure()
    plt.plot(x, y, marker='x', label='dfunc')  # The marker highlights the individual points.

    if depths is not None:
        dy = np.interp(depths, x, y, left=0, right=max(y))
        plt.scatter(depths, dy, color='black', label='Depths', marker='O')  # Plot depths as black circles.

    plt.xlabel("exposure")
    plt.ylabel("impacts")
    plt.grid(True)
    plt.legend()
    plt.show()


        
        