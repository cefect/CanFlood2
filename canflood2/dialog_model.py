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
from qgis.gui import QgsFieldComboBox

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
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert not self.model.param_d is None, 'failed to load model parameters'
        
        if not 'finv_elevType' in self.model.param_d.keys():
            raise AssertionError(f'must set the \'Elevation Type\' on the \'Asset Inventory\' tab before compiling the model')
 
 
        #=======================================================================
        # compile sequence
        #=======================================================================
        #asset inventory
        _ = self._table_finv_to_db(**skwargs)
        
        #sample DEM
        _ = self._table_gels_to_db(**skwargs)
            
        #asset exposures
        _ = self._table_expos_to_db(**skwargs)
        
        #=======================================================================
        # wrap
        #=======================================================================
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
        
        field_value_d = {k:model.param_d[v] for k,v in names_d.items() if v in model.param_d.keys()}
 
        
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

        # Ensure all values in the dictionary are present in the dataframe's column names
        assert all(value in df_raw.columns for value in field_value_d.values()), 'Some fields are not found in the dataframe columns'

        
        #standaraize the column names
        df = df_raw.rename(columns={v:k for k,v in field_value_d.items()}).loc[:, field_value_d.keys()]
        
        #add empty columns for any field_value_d.keys() that are missing from the dataframe
        #makes data consistency checks easier
        for k in names_d.keys():
            if k not in df.columns:
                df[k] = pd.NA
        
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
        
        finv_elevType = model.param_d['finv_elevType']
 
        
        log.debug(f'building table_gels for finv_elevType={finv_elevType}')
        
        
                    
        #=======================================================================
        # load finv
        #=======================================================================
        finv_indexField = model.param_d['finv_indexField']
        finv_vlay = self.get_finv_vlay()
        
        assert finv_indexField in finv_vlay.fields().names(), 'bad finv_indexField'
        
        #=======================================================================
        # build from DEM
        #=======================================================================
        if finv_elevType == 'relative':
            #=======================================================================
            # load DEM
            #=======================================================================
            dem_rlay = self.parent.get_dem_vlay()
            assert dem_rlay is not None, f'must select a DEM for finv_elevType=\'{finv_elevType}\''
            log.debug(f'loaded dem {dem_rlay.name()}')

            
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
            samples_s = vlay_to_df(QgsVectorLayer(samples_fp, 'samples')).set_index(finv_indexField
                                                                    )['dem_1'].rename('dem_samples')
            samples_s.index.name = finv_index.name
            
        elif finv_elevType == 'absolute':
            log.debug(f'building blank table_gels for finv_elevType={finv_elevType}')
            #===================================================================
            # blank dummy table
            #===================================================================
            #extract a series from the vector layer
            #df_raw = vlay_to_df(finv_vlay)
            
            #load the finv table from the databawse
            #note: table_finv is multindex, but table_gels is not
            index = model.get_tables(['table_finv'])[0].index.get_level_values('indexField')
 
            samples_s = pd.Series(pd.NA,index=index, name='dem_samples')
            
        else:
            raise KeyError(f'unknown finv_elevType: {finv_elevType}')
            
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
    
 
class Model_config_dialog_assetInventory(object):
    """organizer for Asset Inventory toolbox"""
    functionGroups_widget_type_d= {
        'label_functionGroupID':QLabel,
        'mFieldComboBox_cap':QgsFieldComboBox,
        'mFieldComboBox_elev':QgsFieldComboBox,
        'mFieldComboBox_scale':QgsFieldComboBox,
        'mFieldComboBox_tag':QgsFieldComboBox,
        'pushButton_mod_minus':QPushButton,
        'pushButton_mod_plus':QPushButton,
        
        
        }
    
    functionGroups_finv_tags_d = { #see also parameters.modelTable_params_d['table_finv']
        'mFieldComboBox_cap':'cap',
        'mFieldComboBox_elev':'elev',
        'mFieldComboBox_scale':'scale',
        'mFieldComboBox_tag':'tag',
        
        }
    
    
    
    def _connect_slots_assetInventory(self, log):
        """asset inventory related slot connections"""
        
        
        #connect the vector layer
        bind_MapLayerComboBox(self.comboBox_finv_vlay, 
                              iface=self.iface, 
                              layerType=QgsMapLayerProxyModel.VectorLayer)
 
        
        #bind the exposure geometry label
        def update_finv_geometry_label():
            layer = self.comboBox_finv_vlay.currentLayer()
            if not layer is None:
                self.label_EX_geometryType.setText(QgsWkbTypes.displayString(layer.wkbType()))
            
        self.comboBox_finv_vlay.layerChanged.connect(update_finv_geometry_label)
        

        
        #=======================================================================
        # Advanced Tab: Function Groups
        #=======================================================================
        self.functionGroups_index_d=dict()
        
        #create the first function group
        _, _, FG_widget_d = self._add_function_group()
        
        """
        this is a mirror of the main function group on the Data Selection tab
        connecting all the DataSelection comboboxes so they update these ones"""
 
        #build the first group widget bindings dict (on main Data Selection tab)
        self.functionGroup0_widget_d = {
            'xid': self.mFieldComboBox_cid,
            'scale': self.mFieldComboBox_AI_01_scale,
            'tag': self.mFieldComboBox_AI_01_tag,
            'elev': self.mFieldComboBox_AI_01_elev,
            'cap': self.mFieldComboBox_AI_01_cap,
        }

 
        
        #=======================================================================
        # #finv bindings
        #=======================================================================
        #loop through and connect all the field combo boxes to the finv map layer combo box
        for tag, comboBox in self.functionGroup0_widget_d.items():
            
            fn_str = 'f0_' + tag
            
            bind_QgsFieldComboBox(comboBox, 
                                  signal_emitter_widget=self.comboBox_finv_vlay,
                                  fn_str=fn_str)
            
            #connect Advanced Tab as downstream widgets
            if not tag=='xid':
                #retreive the AdvancedTab widget
                w= None
                for k,d in FG_widget_d.items():
                    if d['tag']==tag:
                        w = d['widget']
                assert not w is  None, 'failed to find widget for tag %s'%fn_str
                
                #disable the downstream
                w.setEnabled(False)
 
                #connect it to the advganced tab downstream widget
                comboBox.connect_downstream_combobox(w)
                
            
        #set the optionals
        for cbox in [ self.mFieldComboBox_AI_01_tag, self.mFieldComboBox_AI_01_cap]:
            cbox.setAllowEmptyFieldName(True)
            cbox.setCurrentIndex(-1)
        
        #bind the asset label to the update_labels such that any time it changes the function runs
        """not sure about this... leaving this dependent on teh projDB fo rnow
        self.labelLineEdit_AI_label.tesxtChanged(self.update_labels)
        #self.label_mod_asset.setText(s['asset_label'])"""
        

        
    def get_finv_vlay(self):
        """get the asset inventory vector layer"""
        vlay = self.comboBox_finv_vlay.currentLayer()
        assert not vlay is None, 'no vector layer selected'
        
        assert isinstance(vlay, QgsVectorLayer), f'bad type: {type(vlay)}'
        
        #check that it is a point layer
        if not vlay.geometryType() == QgsWkbTypes.PointGeometry:
            raise NotImplementedError(f'geometry type not supported: {QgsWkbTypes.displayString(vlay.wkbType())}')
         
        
        return vlay
    
    def _add_function_group(self):
        """ui endpoint for add a function group widget to the advanced tab
        
        NOTE: for adding from the projDB, see self.load_model()
        """
        log = self.logger.getChild('_add_function_group')
        log.debug('adding function group widget')
        
        #get the index
        fg_index = len(self.functionGroups_index_d)
        assert not fg_index in self.functionGroups_index_d, f'index {fg_index} already exists'        
        
        #build the UI
        log.debug(f'adding function group {fg_index}')
        widget, widget_d = self._add_function_group_ui(fg_index)
            
            
        #add to the index
        self.functionGroups_index_d[fg_index] = {'widget':widget, 'child_d':widget_d}
        
        log.info(f'added function group {fg_index+1}/{len(self.functionGroups_index_d)} to the advanced tab')
        
        return fg_index, widget, widget_d
        
    def _add_function_group_ui(self, fg_index):
        """setup the UI for the function group
        called by _add_function_group()
        making this separate for assigning actions
        """
        
        log = self.logger.getChild('_add_function_group_ui')
        layout = self.groupBox_AI_03_functionGroups.layout()            
        
        #load the widget
        widget = load_functionGroup_widget_template()
        layout.addWidget(widget)
        
        #loop through each widget element and make a reference
        widget_d = dict()
        for name, widget_type in self.functionGroups_widget_type_d.items():
            child_widget = widget.findChild(widget_type, name)
            assert isinstance(child_widget, widget_type), f'failed to find widget: {name}'
            widget_d[name] = {'name':name, 'widget':child_widget}
            
            if name in self.functionGroups_finv_tags_d.keys():
                widget_d[name]['tag'] = self.functionGroups_finv_tags_d[name]
            else:
                widget_d[name]['tag'] = None    
            
        
        log.debug(f'added   {len(widget_d)} widgets') 
            
        #=======================================================================
        # bindings
        #=======================================================================
        #set the label
        widget.label_functionGroupID.setText(str(fg_index))
            
        #bind the new buttons
        widget.pushButton_mod_minus.clicked.connect(
            lambda: self._remove_function_group(fg_index)
            )
        
        widget.pushButton_mod_plus.clicked.connect(
            lambda: self._add_function_group()
            )
        
        #vbind the field combo boxes to the finv vector layer
        cnt = 0
        for name, widget_type in self.functionGroups_widget_type_d.items():
            if widget_type == QgsFieldComboBox:
                w = widget_d[name]['widget']
                tag = widget_d[name]['tag']
                bind_QgsFieldComboBox(w, 
                                      signal_emitter_widget=self.comboBox_finv_vlay,
                                      fn_str=tag)
                
                cnt += 1
                
                #set optionals
                #===============================================================
                # if tag in ['cap', 'tag']:
                #     w.setAllowEmptyFieldName(True)
                #     w.setCurrentIndex(-1)
                #===============================================================
        
        log.debug(f'bound {cnt} field combo boxes to the finv vector layer')
                
        
 
        
 
        
        return widget, widget_d
        
    def _remove_function_group(self, fg_index):
        """
        remove a function group widget from the advanced tab
        """
        log = self.logger.getChild('_remove_function_group')
        log.debug(f'removing function group {fg_index}')
        
        d = self.functionGroups_index_d[fg_index]
        widget, child_d = d['widget'], d['child_d']
        
        #=======================================================================
        # remove the widget
        #=======================================================================
 
        
        parent = widget.parent()
 
        if parent is not None:
            layout = parent.layout()  # Get the parent's layout
            if layout is not None:
                layout.removeWidget(widget)
        widget.setParent(None)   # Detach the widget from its parent
        widget.deleteLater()     # Schedule the widget for deletion
        widget=None
        
        self.functionGroups_index_d[fg_index]['widget'] = None  # Clear the reference to the widget
        
        #=======================================================================
        # clear the index entry   
        #=======================================================================
        del self.functionGroups_index_d[fg_index]
        
        log.debug('removed function group %d'%fg_index)
        
    def _remove_function_group_all(self):
        """remove all function groups from the advanced tab"""
        log = self.logger.getChild('_remove_function_group_all')
        
        log.debug('removing all function groups')
        
        #loop through and remove each
        cnt=0
        for fg_index in sorted(self.functionGroups_index_d.keys(), reverse=True):
            self._remove_function_group(fg_index)
            cnt+1
            
        assert len(self.functionGroups_index_d) == 0, 'failed to remove all function groups'
        log.debug(f'removed {cnt} function groups')
        
        self.functionGroups_index_d=dict()
            
        
        
    
 


class Model_config_dialog(Model_compiler, Model_config_dialog_assetInventory, 
                          QtWidgets.QDialog, FORM_CLASS):
    
    
    
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
        self.pushButton_save.clicked.connect(self._save)
        
        self.pushButton_close.clicked.connect(self._close)
        self.pushButton_run.clicked.connect(self._run_model)
        
        #=======================================================================
        # Asset Inventory--------
        #=======================================================================
        self._connect_slots_assetInventory(log)
        
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
        
        #set the pushButton_V_vfunc_load button to enable when comboBox_expoLevel='L2'
        self.pushButton_V_vfunc_load.setEnabled(False)
        self.comboBox_expoLevel.currentIndexChanged.connect(
            lambda: self.pushButton_V_vfunc_load.setEnabled('L2' in self.comboBox_expoLevel.currentText())
            )
        
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
        
        #=======================================================================
        # static
        #=======================================================================
        #get just those with values
        df1 = params_df.loc[:, ['widgetName', 'value', 'dynamic']].dropna(subset=['value', 'widgetName']
                                       ).set_index('widgetName')
                                       
        static_d = df1.loc[~df1['dynamic']].drop('dynamic', axis=1).iloc[:, 0].to_dict()                              
                                       
                                       
 
        if len(static_d)>0:
            log.debug(f'loading {len(static_d)} parameters for model {model.name}')
            for k,v in static_d.items():
                if not hasattr(self, k):
                    raise KeyError(f'widget {k} not found in dialog')
                widget = getattr(self, k)
                set_widget_value(widget, v)
 
                
        else:
            log.debug(f'paramter table empty for model {model.name}')
            
        #=======================================================================
        # dynamic: function Groups
        #=======================================================================
        if not params_df['fg_index'].notna().any():
            log.warning('no function groups found in the parameters table... skipping load')
            
        else:
 
            
     
            #load the group values from the parameter table
            df1 = params_df[params_df['fg_index'].notna()].set_index('varName')
            df1 = df1.dropna(subset=['value']).drop(['required', 'dynamic', 'model_index'], axis=1)
            df1 = df1.astype({'fg_index':'int64'}).sort_values('fg_index')
            
            #add tags
            df1['tag'] = df1.index.str.replace(r"f(\d+)_", "", regex=True)
            
            #check that the fg_index is monotonic starting at zero
            assert df1['fg_index'].min() == 0, 'fg_index must start at zero'
            assert df1['fg_index'].max() == df1['fg_index'].nunique()-1, 'fg_index must be monotonic'
            
            #loop through each function group and populate the UI
            
            log.debug(f'loading {len(df1)} function groups for model {model.name}')
            
            cnt=0
            for fg_index, gdf in df1.groupby('fg_index'):
                gdf = gdf.reset_index().set_index('tag').sort_index().drop('fg_index', axis=1)
                
                #first group
                if fg_index==0:
                    """dont want to destroy/recreate the UI here as it is connected"""
                    assert fg_index in self.functionGroups_index_d, 'expected FG0 to be on the advanced tab already'
                    
                    log.debug(f'adding FG0')
                    #used for checking
                    advanced_child_d = {d['tag']:d for k,d in self.functionGroups_index_d[fg_index]['child_d'].items() if not d['tag'] is None}
                    
                    #set the parameters on hte main widgets
                    for k, v in gdf['value'].items():
 
                        
                        #get the main widget
                        assert k in self.functionGroup0_widget_d.keys(), f'unknown tag: {k}'
                        
                        #set
                        """NOTE: this should be linked to the advanced widget"""
                        set_widget_value(self.functionGroup0_widget_d[k], v)
                        
                        #check the Advanced tab link
                        advanced_w = advanced_child_d[k]['widget']
                        assert get_widget_value(advanced_w) == v, f'widget {k} not set correctly: {get_widget_value(advanced_w)} != {v}'
                    
                    
                #advanced gruops
                #NOTE: only relevent for L2 models
                else:
                    #destroy any existing
                    if fg_index in self.functionGroups_index_d.keys():
                        self._remove_function_group(fg_index)
                        log.debug(f'removed function group {fg_index}')
                
                    #build the UI
                    log.debug(f'adding function group {fg_index}')
                    widget, widget_d = self._add_function_group_ui(fg_index)
                        
                        
                    #add to the index
                    self.functionGroups_index_d[fg_index] = {'widget':widget, 'child_d':widget_d}
                    
                    #set the widget values from the parameters
                    wTag_d = {d['tag']:d for k,d in widget_d.items() if not d['tag'] is None}
                    for k, v in gdf['value'].items():                        
                        set_widget_value(wTag_d[k]['widget'], v)
                
                #wrap
                log.debug(f'finished adding function group {fg_index} with {len(gdf)} parameters')
                cnt+=1
            #wrap
            log.debug(f'finished loading {cnt} function groups for model {model.name}')
                        
 
 
            
            
        
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
        # collect static--------
        #=======================================================================
        #loop through each widget and collect the state from the ui
        d = dict()
        for i, widgetName in params_df['widgetName'].dropna().items():
            
            widget = getattr(self, widgetName)
            d[i] = get_widget_value(widget)
            
        #update
        s = pd.Series(d, name='value').replace('', pd.NA) 
        
        #update the parameters table with the ui state
        params_df.loc[s.index, 'value'] = s
        
        
        #=======================================================================
        # collect dynamic: FunctionGroups-----
        #=======================================================================
        d=dict()
        #those parameters not fo und in the params_df because they are generated
        index_d = self.functionGroups_index_d
        log.debug(f'collecting functionGroup params on {len(index_d)} function groups')
        cnt = 0
        for i, (fg_index, data_d) in enumerate(index_d.items()):

            #loop through each child and collect
            for j, (name, widget_d) in enumerate(data_d['child_d'].items()):
                tag, widget = widget_d['tag'], widget_d['widget']
                if not tag is None:
                    cnt+=1
                    #retrieve the fieldName from teh widget
                    v = get_widget_value(widget)
                    
                    #check if the result is None or null
                    if v is None or v == '':
                        log.debug(f'    skipping {tag} for function group {fg_index} as it is empty')
                        continue
                    
                    #store in the container
                    k = 'f%d_%s'%(fg_index, tag)
                    assert not k in d.keys(), f'key {k} already exists in the parameter dictionary'
                    #d[k] = v
                    log.debug(f'    got \'{k}\'={v}')
 
                    d[cnt] = {'varName':k, 'widgetName':name, 'value':v, 
                         'required':False, 'dynamic':True,
                         'model_index':False, #whether the field should be included in the model_index table
                         'fg_index':fg_index,                   
                        }
        
        #check
 
        log.debug(f'collected {len(d)} functionGroup parameters')
        
 
        
        #update
        if len(d)>0:
            dyn_df = pd.DataFrame.from_dict(d, orient='index').set_index('varName')
            
            assert dyn_df['fg_index'].max()+1==len(index_d), 'fg_index mismatch'
            
            #check the columns are identical
            assert set(params_df.columns) == set(dyn_df.columns), 'columns mismatch'
            
            #concatenate the two dataframes
            params_df = pd.concat([params_df, dyn_df], axis=0)
            
        
        #=======================================================================
        # precheck
        #=======================================================================
        #=======================================================================
        # """mostly for not-implemented things"""
        # if not d['expo_level']== 'depth-dependent (L2)':
        #     raise AssertionError(f'only depth-dependent (L2) exposure level is supported at this time')
        #=======================================================================
        
            

        
        #=======================================================================
        # update
        #=======================================================================

 
  
        
        #write to the parent
        model.set_tables({'table_parameters':params_df.reset_index()}, logger=log)
        
        #=======================================================================
        # update model index
        #=======================================================================
        """called by set_tables()
        self.parent.update_model_index_dx(model, logger=log)"""
        
        log.push(f'saved {len(s)} parameters for model {model.name}')
        
        

        

 
        
        
    def _run_model(self, *args, compile_model=True):
        """run the model
        
        no longer saves... user must save first
            should probably add a 'have you saved yet' check/dialog
        
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
        
 
        try:
            #store the UI state
            self.progressBar.setValue(5)
    #===========================================================================
    #         self._set_ui_to_table_parameters(**skwargs)
    #         
    # 
    #         #=======================================================================
    #         # compiling
    #         #=======================================================================
    #         self.progressBar.setValue(20)
    #         if compile_model:
    #             self.compile_model(**skwargs)
    #===========================================================================
            
            #=======================================================================
            # run it
            #=======================================================================
            #self.progressBar.setValue(50)
            result = model.run_model(projDB_fp=self.parent.get_projDB_fp(),
                            progressBar=self.progressBar)
            
            #=======================================================================
            # wrap
            #=======================================================================
            self.progressBar.setValue(100)
            log.push(f'finished running model {model.name}')
        except Exception as e:
            log.error(f'failed to run model {model.name}')
            log.info(f'failed to run model {model.name} w/ \n     {e}')
            
            self.progressBar.setValue(0)
            
            raise
            
        

    def xxx_save_and_close(self):
        """save the dialog to the model parameters table
        removed the OK button and replaced with save
        """
 
        log = self.logger.getChild('_save_and_close')
        log.debug('closing')
        
        model = self.model
        
        #=======================================================================
        # retrieve, set, and save the paramter table
        #=======================================================================
        self.model.compute_status()
        
        self._set_ui_to_table_parameters(model, logger=log)     
        
        
 
        #=======================================================================
        # close
        #=======================================================================
        self._custom_cleanup()
        log.info(f'finished saving model {model.name}')
        self.accept()
        
    def _save(self, *args, model=None, logger=None):
        """save the paramterse and compile the model"""
 
        #defaults
        if logger is None: logger = self.logger
        
        log = logger.getChild('_save')
        log.info('saving model to ProjDB')
        
        if model is None: model = self.model
        assert isinstance(model, Model)
 
        self.progressBar.setValue(5)
        
        #=======================================================================
        # retrieve, set, and save the paramter table
        #=======================================================================
        model.compute_status()
        self.progressBar.setValue(30)
        
        self._set_ui_to_table_parameters(model=model, logger=log)
        self.progressBar.setValue(50) 
        
        self.compile_model(model=model, logger=log) 
        self.progressBar.setValue(100)        
        
 
        #=======================================================================
        # wrap
        #=======================================================================
        log.info(f'finished saving model {model.name}')
        self.progressBar.setValue(0)
        
    def _close(self):
        """close the dialog without saving
        
        TODO: save check with dialog"""
 
        self._custom_cleanup()
        self.reject()
        
    def _custom_cleanup(self):
        
        self.parent._update_model_widget_labels(model=self.model)
        self.model.Model_config_dialog=None
        
        self.model=None
        
        
#===============================================================================
# HERLPERS--------
#===============================================================================
 
def load_functionGroup_widget_template(
    template_ui = os.path.join(os.path.dirname(__file__), 'canflood2_model_functionGroup_widget.ui'), 
    parent=None,
    ):
    
    """load the model widget template"""
 
    widget = QtWidgets.QWidget(parent)
    uic.loadUi(template_ui, widget)
    return widget
        
        
        
        
        
        
        
        

