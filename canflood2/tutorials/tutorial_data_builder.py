"""
Created on Mar 20, 2025
@author: cef

Helpers for loading tutorial data to the UI.
 

tutorial_lib[tut_name] = {
    'fancy_name'          : str,
    'Main_dialog'         : {
        'data'   : {...},      # project-wide files (haz, dem, aoi, …)
        'widget' : {...},      # Main-dialog widget values
    },
    'models'              : {
        'c1': {               # consequence category
            0: {              # modelid
                'widget'          : {...},   # model-config widget values
                'data'            : {...},   # model-specific files (finv, vfunc, …)
                'function_groups' : (...),   # optional advanced groups
            }
        }
    },
}
"""

import os
import copy
import pprint                       # noqa: F401  (handy for debugging)
from ..parameters import src_dir     # noqa: F401  (import kept for API parity)

# ────────────────────────── paths & defaults ────────────────────────────
test_data_dir = os.path.join(os.path.dirname(__file__), "data")
assert os.path.exists(test_data_dir), f"Missing test-data dir: {test_data_dir}"

default_data_d = {
    "haz": {
        50: "haz_0050.tif",
        100: "haz_0100.tif",
        200: "haz_0200.tif",
        1_000: "haz_1000.tif",
    },
    "dem": "dem_rlay.tif",
    "aoi": "aoi_vlay.geojson",
    "eventMeta": "eventMeta_df.csv",
}

# ───────────────────────── tutorial ❶  (L1 basic) ───────────────────────
tutorial_lib = {
    "cf1_tutorial_01": {
        "fancy_name": "Tutorial 1",
        "Main_dialog": {
            # no DEM for L1
            "data": {k: v for k, v in default_data_d.items() if k != "dem"},
            "widget": {
                "scenarioNameLineEdit": "undefended",
                "climateStateLineEdit": "historical climate",
                "hazardTypeLineEdit": "fluvial",
                "radioButton_ELari": "1",  # 0 = AEP
            },
        },
        "models": {
            "c1": {
                0: {
                    "widget": {
                        "comboBox_expoLevel": "binary (L1)",
                        "comboBox_AI_elevType": "absolute",
                        "mFieldComboBox_cid": "xid",
                        "mFieldComboBox_AI_01_scale": "f0_scale",
                        "mFieldComboBox_AI_01_elev": "f0_elev",
                        "labelLineEdit_AI_label": "houses",
                        "consequenceLineEdit_V": "displacement",
                        "comboBox_R_highPtail": "none",
                        "comboBox_R_lowPtail": "extrapolate",
                        "doubleSpinBox_R_lowPtail": 1e9,
                        "doubleSpinBox_R_highPtail": 0.1,
                    },
                    "data": {
                        "finv": "finv_tut1a.geojson",
                    },
                    #FunctionGroup goes here
                }
            }
        },
    }
}

# ─────────────────── helper for Tutorial-2 base (L2) ────────────────────
def _build_tut2_base(fancy_name: str) -> dict:
    return {
        "fancy_name": fancy_name,
        "Main_dialog": {
            "data": copy.deepcopy(default_data_d),
            "widget": {
                "scenarioNameLineEdit": "undefended",
                "climateStateLineEdit": "historical climate",
                "hazardTypeLineEdit": "fluvial",
                "radioButton_ELari": "1",  # ARI by default
            },
        },
        "models": {
            "c1": {
                0: {
                    "widget": {
                        "comboBox_expoLevel": "depth-dependent (L2)",
                        "comboBox_AI_elevType": "relative",
                        "mFieldComboBox_cid": "xid",
                        "mFieldComboBox_AI_01_scale": "f0_scale",
                        "mFieldComboBox_AI_01_elev": "f0_elev",
                        "mFieldComboBox_AI_01_tag": "functionName",
                        "mFieldComboBox_AI_01_cap": "f0_cap",
                        "labelLineEdit_AI_label": "buildings",
                        "consequenceLineEdit_V": "replacement cost",
                        "comboBox_R_highPtail": "none",
                        "comboBox_R_lowPtail": "extrapolate",
                        "doubleSpinBox_R_lowPtail": 1e9,
                        "doubleSpinBox_R_highPtail": 0.1,
                    },
                    "data": {
                        "finv": "finv_tut2.geojson",
                        "vfunc": "vfunc.xls",
                    },
                }
            }
        },
    }


# ────────────── Tutorial 2 a (ARI)  ─────────────
tutorial_lib["cf1_tutorial_02"] = _build_tut2_base("Tutorial 2a")

# ────────────── Tutorial 2 b (AEP) ──────────────
tutorial_lib["cf1_tutorial_02b"] = copy.deepcopy(tutorial_lib["cf1_tutorial_02"])
t2b = tutorial_lib["cf1_tutorial_02b"]
t2b["fancy_name"] = "Tutorial 2b (AEP)"
t2b["Main_dialog"]["widget"]["radioButton_ELari"] = "0" #aep
t2b["Main_dialog"]["data"]["eventMeta"] = "eventMeta_df_aep.csv"

# ────────────── Tutorial 2 c (finv heights) ─────
tutorial_lib["cf1_tutorial_02c"] = copy.deepcopy(tutorial_lib["cf1_tutorial_02"])
t2c = tutorial_lib["cf1_tutorial_02c"]
t2c["fancy_name"] = "Tutorial 2c (finv heights)"
mdl2c = t2c["models"]["c1"][0]
mdl2c["data"]["finv"] = "finv_tut2_elev.geojson"
mdl2c["widget"]["comboBox_AI_elevType"] = "absolute"

# ────────────── Tutorial 2 d (extra function groups) ──
tutorial_lib["cf1_tutorial_02d"] = copy.deepcopy(tutorial_lib["cf1_tutorial_02"])
t2d = tutorial_lib["cf1_tutorial_02d"]
t2d["fancy_name"] = "Tutorial 2d (functionGroups)"
t2d["models"]["c1"][0]["FunctionGroup"] = (
    {"cap": "f1_cap", "elev": "f1_elev", "scale": "f1_scale", "tag": "f1_tag"},
)

# ────────────── Tutorial 2 d.2 (over-lapping cols) ──
tutorial_lib["cf1_tutorial_02d_2"] = copy.deepcopy(tutorial_lib["cf1_tutorial_02d"])
t2d2 = tutorial_lib["cf1_tutorial_02d_2"]
t2d2["fancy_name"] = "Tutorial 2d.2 (functionGroups2)"
t2d2["models"]["c1"][0]["FunctionGroup"] = (
    {"cap": "f1_cap", "elev": "f1_elev", "scale": "f1_scale", "tag": "functionName"},
)

#===============================================================================
# Tutorial 2e: 2 models----------
#===============================================================================
tutorial_lib["cf1_tutorial_02e"] = copy.deepcopy(tutorial_lib["cf1_tutorial_02"])
t2e = tutorial_lib["cf1_tutorial_02e"]
t2e["fancy_name"] = "Tutorial 2e (two models)"

#just use data from tutorial1
t2e["models"]["c2"] = copy.deepcopy(tutorial_lib["cf1_tutorial_02c"]["models"]["c1"])
 
 
# ───────────────────── helpers ─────────────────────
def _basename(fp: str) -> str:
    """Return the file name without path or extension."""
    return os.path.splitext(os.path.basename(fp))[0]


def _abs(fp: str) -> str:
    """Convert a relative file name to an absolute path under *test_data_dir*."""
    path = os.path.join(test_data_dir, fp)
    assert os.path.exists(path), f"Missing file: {path}"
    return path


# ───────── add finv layer-names to model widgets ─────────
for tut in tutorial_lib.values():
    for consequence_category, d0 in tut["models"].items():
        for modelid, d1 in d0.items():
            finv_fp = d1["data"].get("finv")
            if not isinstance(finv_fp, str):
                raise TypeError('"finv" must be a string')
            
            d1["widget"]["comboBox_finv_vlay"] = _basename(finv_fp)

# ─────── convert every filename to a full path ────────
for tut in tutorial_lib.values():
    # project-level data
    for k, v in tut["Main_dialog"]["data"].items():
        #simples
        if isinstance(v, str):
            tut["Main_dialog"]["data"][k] = _abs(v)
            
        #hazard layers
        elif isinstance(v, dict):
            # convert dict values to absolute paths
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, str):
                    v[sub_k] = _abs(sub_v)
                else:
                    raise TypeError(f'Expected "data" value to be a string, got {type(sub_v)}')
        else:
            raise TypeError(f'Expected "data" value to be a string, got {type(v)}')

    # model-level data
    for consequence_category, d0 in tut["models"].items():
        for modelid, d1 in d0.items():
            #loop through all the data
            for k, v in d1["data"].items():
                if isinstance(v, str):
                    d1["data"][k] = _abs(v)
                else:
                    raise TypeError(f'Expected "data" value to be a string, got {type(v)}')
 

# ───────────────── attach existing project DBs ─────────────────
proj_db_dir = os.path.join(test_data_dir, "projDBs")
assert os.path.exists(proj_db_dir), f"Missing projDB dir: {proj_db_dir}"

for fn in os.listdir(proj_db_dir):
    if fn.endswith(".canflood2"):
        tut_name = os.path.splitext(fn)[0]
        assert tut_name in tutorial_lib, f"No tutorial named {tut_name}"
        tutorial_lib[tut_name]["Main_dialog"]["data"]["projDB"] = os.path.join(
            proj_db_dir, fn
        )

# ─────────────── fancy-name lookup & study areas ──────────────
tutorial_fancy_names_d = {
    tut["fancy_name"]: name for name, tut in tutorial_lib.items()
}

for name, tut in tutorial_lib.items():
    fancy = tut["fancy_name"]
    tut["Main_dialog"]["widget"]["studyAreaLineEdit"] = f"{name} ({fancy})"

# ─────────────────── summary ────────────────────
print(f"Loaded {len(tutorial_lib)} tutorials from\n    {test_data_dir}")
# pprint.pprint(tutorial_lib)  # uncomment for a full dump








