'''
Created on Mar 6, 2025

@author: cef
ui dialog class for model config window
'''

#==============================================================================
# imports-----------
#==============================================================================
#python
import sys, os, datetime, time, configparser, logging, sqlite3
import pandas as pd

from pandas.testing import assert_index_equal

from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QListWidget, QTableWidgetItem, QDoubleSpinBox,
    QLabel, QPushButton, QProgressBar
    )

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsMapLayerProxyModel,
    QgsWkbTypes, QgsMapLayer, QgsLogger,
    )

from .hp.basic import view_web_df as view
from .hp.qt import set_widget_value, get_widget_value
from .hp.plug import bind_QgsFieldComboBox, bind_MapLayerComboBox, plugLogger
from .hp.Q import vlay_to_df, ProcessingEnvironment

from .assertions import assert_projDB_fp, assert_vfunc_fp, assert_projDB_conn

from .parameters import (
    consequence_category_d, home_dir, project_db_schema_d, finv_index,plugin_dir
    )
from .hp.vfunc import  load_vfunc_to_df_d, vfunc_df_to_dict, vfunc_cdf_chk_d, vfunc_df_to_meta_and_ddf
from .db_tools import sql_to_df

from .core import Model


#===============================================================================
# load UI and resources
#===============================================================================

#append the path (resources_rc workaround)
resources_module_fp = os.path.join(plugin_dir, 'resources.py')
assert os.path.exists(resources_module_fp), resources_module_fp 
if not os.path.dirname(resources_module_fp) in sys.path:
    sys.path.append(os.path.dirname(resources_module_fp))

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'canflood2_model_config.ui')
assert os.path.exists(ui_fp), f'UI file not found: {ui_fp}'
FORM_CLASS, _ = uic.loadUiType(ui_fp, resource_suffix='') #Unknown C++ class: Qgis

 

#===============================================================================
# Dialog class------------------
#===============================================================================

class Model_compiler(object):
    """organizer for model compilation functions
    
    
    here we build projDB tables specific to the model    
        computation against these tables happens in core
        
    consider making this a separate buttton?
        equivalent to CanFloodv1's 'Build' routine
    
    """
    
    def compile_model(self, **skwargs):
        """wrapper around compilation sequence"""
        
        assert not self.model.param_d is None, 'failed to load model parameters'
        """run compilation sequence"""
        #asset inventory
        _ = self._table_finv_to_db(**skwargs)
        
        #ground elevations
        if self.model.param_d['finv_elevType'] == 'ground':
            _ = self._table_gels_to_db(**skwargs)
            
        #asset exposures
        _ = self._table_expos_to_db(**skwargs)
        
        assert_projDB_fp(self.parent.get_projDB_fp())
        
        self.update_labels()
    
    
    
    def _table_finv_to_db(self, model=None, logger=None):
        """write the finv table to the database"""
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        if model is None: model = self.model
        
        log = self.logger.getChild('_table_finv_to_db')
 
        #=======================================================================
        # load the data
        #=======================================================================
        #load field names from parameters table
 
        
        """only one nest for now
        using this names_d as a lazy conversion from the model_parameters to the finv table names"""
        names_d = {
            'indexField':'finv_indexField',
            'scale':'f01_scale','elev':'f01_elev','tag':'f01_tag','cap':'f01_cap',
            }
        
        field_value_d = {k:model.param_d[v] for k,v in names_d.items()}
 
        
        #get the vector layer
        vlay = self.get_finv_vlay()
        
        #extract features as a datafram e
        df_raw = vlay_to_df(vlay)
        
        log.debug(f'loaded {df_raw.shape} from {vlay.name()}')
        #=======================================================================
        # process 
        #=======================================================================
        #check that all the field names are in the columns
        #redundant as these come from the FieldBox?
        assert set(field_value_d.values()).issubset(df_raw.columns), 'field not found'
        
        #standaraize the column names
        df = df_raw.rename(columns={v:k for k,v in field_value_d.items()}).loc[:, field_value_d.keys()]
        
        #add the nestID
        df['nestID'] = 0
        
        #move nestID and indexField columns to front
        df = df[['nestID', 'indexField'] + [c for c in df.columns if c not in ['nestID', 'indexField']]]
        
        df = df.astype({'indexField':'int64', 'nestID':'int64'}).set_index(['indexField', 'nestID'])
        
        """
        df.dtypes
        df.index.dtypes
        """
        #=======================================================================
        # #write it to the database
        #=======================================================================
        model.set_tables({'table_finv':df}, logger=log)
        
        log.debug(f'finished')
        return df
    
    def _table_gels_to_db(self, model=None, logger=None):
        """build the ground eleveations table"""
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        if model is None: model = self.model
        
        log = self.logger.getChild('_table_gels_to_db')
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert model.param_d['finv_elevType'] == 'ground', 'bad elevation type'
        
        
        #=======================================================================
        # load DEM
        #=======================================================================
        dem_rlay = self.parent.get_dem_vlay()
        assert dem_rlay is not None, 'must select a DEM for finv_elevType=\'ground\''
        log.debug(f'loaded dem {dem_rlay.name()}')
        
        #=======================================================================
        # load finv
        #=======================================================================
        finv_indexField = model.param_d['finv_indexField']
        finv_vlay = self.get_finv_vlay()
        
        assert finv_indexField in finv_vlay.fields().names(), 'bad finv_indexField'
        
        #=======================================================================
        # sample
        #=======================================================================
        with ProcessingEnvironment(logger=log) as pe: 
            result = pe.run("qgis:rastersampling",
                        { 'COLUMN_PREFIX' : 'dem_', 
                        'INPUT' : finv_vlay, 
                        'OUTPUT' : os.path.join(pe.temp_dir, 'rastersampling_table_gels_to_db.gpkg'), 
                        'RASTERCOPY' : dem_rlay }
                                   )
            
            samples_fp = result['OUTPUT']
            
        #retrieve values
        samples_s = vlay_to_df(QgsVectorLayer(samples_fp, 'samples')).set_index(finv_indexField)['dem_1'].rename('dem_samples')
        samples_s.index.name = finv_index.name
        #=======================================================================
        # write resulting table
        #=======================================================================
        """
        samples_s.dtypes
        samples_s.index.dtype
        """
        model.set_tables({'table_gels':samples_s.to_frame()}, logger=log)
        
        
        
    def _table_expos_to_db(self, model=None, logger=None):
        """build the exposure table"""
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        if model is None: model = self.model
        log = logger.getChild('_table_expos_to_db')
        #=======================================================================
        # load hazard rasters
        #=======================================================================
        haz_rlay_d = self.parent.get_haz_rlay_d()
        assert len(haz_rlay_d) > 1, 'must provide at least one hazard event'
        log.debug(f'loaded {len(haz_rlay_d)} hazard rasters')
        
        #check consistency against event metadata
        haz_events_df = self.parent.projDB_get_tables(['05_haz_events'])[0]        
        assert set(haz_rlay_d.keys()) == set(haz_events_df['event_name']), 'mismatch on hazard events'
        
        #=======================================================================
        # load the finv
        #=======================================================================
        finv_indexField = model.param_d['finv_indexField']
        finv_vlay = self.get_finv_vlay()
        
        assert finv_indexField in finv_vlay.fields().names(), 'bad finv_indexField'
        
        #=======================================================================
        # loop through and sample each
        #=======================================================================
        log.info(f'sampling {len(haz_rlay_d)} hazard rasters w/ {finv_vlay.name()}')
        
       
        samples_d = dict()
        with ProcessingEnvironment(logger=log) as pe: 
            
            for i, (event_name, haz_rlay) in enumerate(haz_rlay_d.items()):
                log.info(f'sampling ({i}/{len(haz_rlay_d)}) on {event_name}')
                result = pe.run("qgis:rastersampling",{
                    'COLUMN_PREFIX' : 'samples_',
                    'INPUT' : finv_vlay,
                    'OUTPUT' : 'TEMPORARY_OUTPUT',
                    'RASTERCOPY' : haz_rlay,
                     })
                
                #retrieve values
                samples_d[event_name] = vlay_to_df(result['OUTPUT']).set_index(finv_indexField)['samples_1']
            
 
        #collect
        expos_df = pd.concat(samples_d, axis=1)
        
            
        log.info(f'finished sampling {expos_df.shape} hazard rasters')
        
        #=======================================================================
        # check
        #=======================================================================
        assert expos_df.index.is_unique, 'non-unique index'
        
        assert_index_equal(expos_df.index,vlay_to_df(finv_vlay).set_index(finv_indexField).index)
        
        #=======================================================================
        # write
        #=======================================================================
        expos_df.index.name='indexField'
        model.set_tables({'table_expos':expos_df}, logger=log)
        
        return expos_df
    
 
        
        
            
        
        
    
 


class Model_config_dialog(Model_compiler, QtWidgets.QDialog, FORM_CLASS):
    
    
    
    def __init__(self, 
                 iface, 
                 parent=None,
                 debug_logger=None,

                 ):
        """called on stawrtup"""
        super(Model_config_dialog, self).__init__(parent) #only calls QtWidgets.QDialog
        
 
        self.parent=parent
        self.iface = iface
        
        self.setupUi(self)
        
        
        #setup logger
        #self.logger=logger.getChild('model_config')
        self.logger = plugLogger(
            iface=self.iface, parent=self, statusQlab=self.progressText,debug_logger=debug_logger,
            log_nm='MC',
            )
        
        self.connect_slots()
        
        self.logger.debug('Model_config_dialog initialized')
        
    def connect_slots(self):
        """on launch of ui, populate and connect"""
 
        log = self.logger.getChild('connect_slots')
        log.debug('connecting slots')
 
        #=======================================================================
        # generic-------
        #=======================================================================
        self.pushButton_ok.clicked.connect(self._save_and_close)
        self.pushButton_close.clicked.connect(self._close)
        self.pushButton_run.clicked.connect(self._run_model)
        
        #=======================================================================
        # Asset Inventory--------
        #=======================================================================
        bind_MapLayerComboBox(self.comboBox_finv_vlay, iface=self.iface, layerType=QgsMapLayerProxyModel.VectorLayer)
 
        
        #bind the exposure geometry label
        def update_finv_geometry_label():
            layer = self.comboBox_finv_vlay.currentLayer()
            if not layer is None:
                self.label_EX_geometryType.setText(QgsWkbTypes.displayString(layer.wkbType()))
            
        self.comboBox_finv_vlay.layerChanged.connect(update_finv_geometry_label)
        
        #=======================================================================
        # #finv bindings
        #=======================================================================
        #loop through and connect all the field combo boxes to the finv map layer combo box
        for comboBox, fn_str in {
            self.mFieldComboBox_cid:'xid',
            self.mFieldComboBox_AI_01_scale:'f0_scale',
            self.mFieldComboBox_AI_01_tag:'f0_tag',
            self.mFieldComboBox_AI_01_elev:'f0_elev',
            self.mFieldComboBox_AI_01_cap:'f0_cap',
            }.items():
            
            bind_QgsFieldComboBox(comboBox, 
                                  signal_emmiter_widget=self.comboBox_finv_vlay,
                                  fn_str=fn_str)
        
        #bind the asset label to the update_labels such that any time it changes the function runs
        """not sure about this... leaving this dependent on teh projDB fo rnow
        self.labelLineEdit_AI_label.tesxtChanged(self.update_labels)
        #self.label_mod_asset.setText(s['asset_label'])"""
        
        #=======================================================================
        # Vulnerability-----------
        #=======================================================================
        def load_vfunc_fp():
            filename, _ = QFileDialog.getOpenFileName(
                self,  # Parent widget (your dialog)
                "Select Vulnerability Function Set",  # Dialog title
                home_dir,  # Initial directory (optional, use current working dir by default)
                "Excel Files (*.xls *.xlsx)",
                )
            if filename:
                self._vfunc_load_from_file(filename)

                
             
        self.pushButton_V_vfunc_load.clicked.connect(load_vfunc_fp)
        
        
        #=======================================================================
        # risk-------
        #=======================================================================
        self.comboBox_R_lowPtail.setCurrentIndex(-1)
        #connect the SpinBox so that it becomes enabled when 'user' is selected in the combobox
        
        self.comboBox_R_lowPtail.currentIndexChanged.connect(
            lambda: self.doubleSpinBox_R_lowPtail.setEnabled(self.comboBox_R_lowPtail.currentText()=='user')
            )
        
        self.comboBox_R_highPtail.setCurrentIndex(-1)
        self.comboBox_R_highPtail.currentIndexChanged.connect(
            lambda: self.doubleSpinBox_R_highPtail.setEnabled(self.comboBox_R_highPtail.currentText()=='user')
            )
        

        
        
        log.debug('slots connected')
        
 
        
    def _vfunc_load_from_file(self, vfunc_fp, logger=None, projDB_fp=None):
        """load the vfunc, do some checks, and set some stats
        
        builds 
            06_vfunc_index
            07_vfunc_data
        
        
        User needs to manually import
        
        only the finv contains a model-specific reference to the vfuncs
            in general, vfuncs are shared across the project
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('_vfunc_load_from_file')
        
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
 
        assert_vfunc_fp(vfunc_fp)
        
        log.info(f'loading vfunc from {vfunc_fp}')
        #=======================================================================
        # get stats
        #=======================================================================
        df_d = load_vfunc_to_df_d(vfunc_fp)      
        

        
        log.debug(f'loaded {len(df_d)} vfuncs from {vfunc_fp}')
        #=======================================================================
        # build index and data table
        #=======================================================================
        #look through each and collect some info
        index_d = dict()
        data_d = dict()
        for k, df in df_d.items():
            #cv_d = vfunc_df_to_dict(df)
            meta_d, ddf = vfunc_df_to_meta_and_ddf(df)
            assert k==meta_d['tag'], 'mismatch on tag on %s'%k
            
            #filter indexers
            """just keep everything
            NO... might get some non-conforming new vfunc sets
            better to just use those from the check dict
            """ 
            index_d[k] = {k:v for k,v in meta_d.items() if k in vfunc_cdf_chk_d.keys()}
            #index_d[k] = meta_d
            
            #collect df-d table
            data_d[k] = ddf
            
        vfunc_index_df = pd.DataFrame.from_dict(index_d, orient='index').reset_index(drop=True)
        vfunc_data_dx = pd.concat(data_d, names=['tag', 'exposure']) 
 
        
        """
        view(index_df)
        """
        
        #create table names
        """NO... using a single data table now
 
        index_df['table_name'] =  'vfunc_' + index_df['tag'].str.replace('_', '')"""        
        
        log.debug(f'built vfunc index w/ {len(vfunc_index_df)} records')
        
 
        #=======================================================================
        # filter based on finv
        #=======================================================================
        """ignoring this for now
        if 'table_finv' in model.get_table_names_all():
            raise NotImplementedError('remove vfuncs not in the finv')
        """
        
        #=======================================================================
        # update projDB
        #=======================================================================
        with sqlite3.connect(projDB_fp) as conn:
            #assert_projDB_conn(conn)
            
            set_df = lambda df, table_name: self.parent.projDB_set_tables({table_name:df}, logger=log, conn=conn)
            #===================================================================
            # # index
            #===================================================================
            table_name = '06_vfunc_index'
            df_old = sql_to_df(table_name, conn)
            
            if len(df_old)==0:
                df = vfunc_index_df
            else:
                raise NotImplementedError(f'need to merge the new vfunc index with the old')
            
            set_df(df.set_index('tag'), table_name)
 
            #===================================================================
            # data
            #===================================================================
            
            table_name='07_vfunc_data'
            df_old = sql_to_df(table_name, conn)
 
            
            if len(df_old)==0:
                df = vfunc_data_dx.reset_index()
            else:
                raise NotImplementedError(f'need to merge the new vfunc data with the old')
            
            set_df(df, table_name)
    
 
            #final consistency check
            #assert_projDB_conn(conn, check_consistency=True)
 
        
        #=======================================================================
        # wrap
        #=======================================================================
        self.update_labels()
        log.info(f'finished loading vfuncs from {os.path.basename(vfunc_fp)}')

        
    def load_model(self, model, projDB_fp=None):
        """load the model worker into the dialog"""
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_model')
        assert isinstance(model, Model), f'bad model type: {type(model)}'
        
        if projDB_fp is None:
            projDB_fp = self.parent.get_projDB_fp()
            
        log.debug(f'loading model {model.name} onto configDialog')
        
        
        #=======================================================================
        # #attach model references
        #=======================================================================
        self.model = model
        model.configDialog = self
        

        #=======================================================================
        # #load parameters from the table to the ui
        #=======================================================================
        params_df = model.get_table_parameters(projDB_fp=projDB_fp)
        """
        view(params_df)
        """
        
        #get just those with values
        params_df = params_df.loc[:, ['widgetName', 'value']].dropna(subset=['value', 'widgetName']
                                       ).set_index('widgetName')
 
        if len(params_df)>0:
            log.debug(f'loading {len(params_df)} parameters for model {model.name}')
            for k,row in params_df.iterrows():
                widget = getattr(self, k)
                set_widget_value(widget, row['value'])
 
                
        else:
            log.debug(f'paramter table empty for model {model.name}')
            
            
            
        
        #=======================================================================
        # update hte labels
        #=======================================================================
        model.compute_status()
        self.update_labels(model=model)
 
        
        
        log.debug(f'finished loaded model {model.name}')
        
        assert not self.model is None, 'failed to load model'
        
    def update_labels(self, model=None):
        """update labels on this UI"""
        log = self.logger.getChild('update_labels')
        if model is None: model = self.model
        
        #=======================================================================
        # top 'model' summary box
        #=======================================================================
        #retrieve from model
        s = model.get_model_index_ser().fillna('')
        
        self.label_mod_modelid.setText('%2d'%model.modelid)
        self.label_mod_asset.setText(s['asset_label'])
        self.label_mod_consq.setText(s['consq_label'])
               
        self.label_category.setText(consequence_category_d[s['category_code']]['desc'])
        
        #=======================================================================
        # #vulnerability tool
        #=======================================================================
        vfunc_index_df = self.parent.projDB_get_tables(['06_vfunc_index'])[0]
        self.label_V_functionCount.setText(str(len(vfunc_index_df)))
        
        #=======================================================================
        # status
        #=======================================================================
        """handled by model
        self.label_mod_status.setText(self.model.status)"""
        model.compute_status()
        
        
        log.debug(f'updated labels for model {model.name}')
        

        
        
        
        

    def _set_ui_to_table_parameters(self, model=None, logger=None):
        """write the model config window parameter state to the approriate table_parameters
        """
        if logger is None: logger = self.logger
        log = logger.getChild('_set_ui_to_table_parameters')
        
        if model is None: model = self.model
        
        #retrieve the parameter table
        params_df = model.get_tables(['table_parameters'])[0].set_index('varName')
        
        """
        view(params_df)
        """
        #=======================================================================
        # collect from ui
        #=======================================================================
        #loop through each widget and collect the state from the ui
        d = dict()
        for i, widgetName in params_df['widgetName'].dropna().items():
            
            widget = getattr(self, widgetName)
            d[i] = get_widget_value(widget)
            

        
        #=======================================================================
        # wrap
        #=======================================================================
        
        s = pd.Series(d, name='value').replace('', pd.NA)
        
        #update the parameters table with the ui state
        params_df.loc[s.index, 'value'] = s
        
        #write to the parent
        model.set_tables({'table_parameters':params_df.reset_index()}, logger=log)
        
        #=======================================================================
        # update model index
        #=======================================================================
        """called by set_tables()
        self.parent.update_model_index_dx(model, logger=log)"""
        
        log.push(f'saved {len(s)} parameters for model {model.name}')
        
        
    def get_finv_vlay(self):
        """get the asset inventory vector layer"""
        vlay = self.comboBox_finv_vlay.currentLayer()
        assert not vlay is None, 'no vector layer selected'
        
        assert isinstance(vlay, QgsVectorLayer), f'bad type: {type(vlay)}'
        
        #check that it is a point layer
        if not vlay.geometryType() == QgsWkbTypes.PointGeometry:
            raise NotImplementedError(f'geometry type not supported: {QgsWkbTypes.displayString(vlay.wkbType())}')
         
        
        return vlay
        

 
        
        
    def _run_model(self, *args, compile_model=True):
        """run the model
        
        Params
        ------
        compile_model: bool
            flag to compile the model before running
            for testing purposes
    
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        self.progressBar.setValue(0)
        log = self.logger.getChild('_run_model')
        model = self.model        
        assert not model is None, 'no model loaded'
        
        skwargs = dict(logger=log, model=model)
        
 
        
        log.info(f'running model {model.name}')
        
        
        #=======================================================================
        # trigger save        
        #=======================================================================
        try:
            self.progressBar.setValue(5)
            self._set_ui_to_table_parameters(**skwargs)
            
    
            #=======================================================================
            # compiling
            #=======================================================================
            self.progressBar.setValue(20)
            if compile_model:
                self.compile_model(**skwargs)
            
            #=======================================================================
            # run it
            #=======================================================================
            self.progressBar.setValue(50)
            model.run_model(projDB_fp=self.parent.get_projDB_fp())
            
            #=======================================================================
            # wrap
            #=======================================================================
            self.progressBar.setValue(100)
            log.push(f'finished running model {model.name}')
        except Exception as e:
            log.error(f'failed to run model {model.name}')
            log.info(f'failed to run model {model.name} w/ \n     {e}')
            
            self.progressBar.setValue(0)
            
        

    def _save_and_close(self):
        """save the dialog to the model parameters table"""
 
        log = self.logger.getChild('_save_and_close')
        log.debug('closing')
        
        model = self.model
        
        #=======================================================================
        # retrieve, set, and save the paramter table
        #=======================================================================
        self.model.compute_status()
        
        self._set_ui_to_table_parameters(model, logger=log)
        
 
 
        self._custom_cleanup()
        log.info(f'finished saving model {model.name}')
        self.accept()
        
    def _close(self):
        """close the dialog without saving"""
 
        self._custom_cleanup()
        self.reject()
        
    def _custom_cleanup(self):
        
        self.parent._update_model_widget_labels(model=self.model)
        self.model.Model_config_dialog=None
        
        self.model=None
        
        
        
        
        
        
        
        
        
        
        
        
        

