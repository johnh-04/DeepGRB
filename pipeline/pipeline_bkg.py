# conda activate deepgrb_recas
# cd DeepGRB
# python -m pipeline.pipeline_bkg
# nohup python -m pipeline.pipeline_bkg > pipeline_runN.log 2>&1 &

import os
import logging
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Headless mode for cluster execution
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ---------------------------------------------------------
# Dynamic Paths Resolution (Strictly Relative)
# ---------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.normpath(os.path.join(script_dir, ".."))

data_dir = os.path.join(base_dir, "data")
cspec_dir = os.path.join(data_dir, "cspec")
bkg_dir = os.path.join(data_dir, "bkg")
nn_model_path = os.path.join(data_dir, "nn_model")
plots_dir = os.path.join(data_dir, "plots")
pred_dir = os.path.join(data_dir, "pred")

# Ensure critical output directories exist
os.makedirs(nn_model_path, exist_ok=True)
os.makedirs(plots_dir, exist_ok=True)
os.makedirs(pred_dir, exist_ok=True)

# ---------------------------------------------------------
# Imports from Project Modules
# ---------------------------------------------------------
from connections.fermi_data_tools import df_burst_catalog, df_trigger_catalog
from models.download_bkg import download_spec
from models.preprocess import build_table
from models.model_nn import ModelNN
from models.trigger import run_trigger
from models.trigs import focus
from models.analyze import analyze
from models.utils.GBMutils import add_trig_gbm_to_frg
from models.localize_event import localize

# ---------------------------------------------------------
# Pipeline Parameters
# ---------------------------------------------------------
erange = {'n': [(28, 50), (50, 300), (300, 500)], 'b': [(756, 5025), (5025, 50000)]}
start_month = "03-2019"
end_month = "07-2019"
pred_file = os.path.join(pred_dir, f"frg_{start_month}_{end_month}.csv")

# ---------------------------------------------------------
# Step 1 & 2: Download and Preprocessing (with caching)
# ---------------------------------------------------------
# Check if prediction file already exists to skip earlier stages completely
need_preprocessing = not (os.path.isfile(pred_file) and os.path.getsize(pred_file) > 0)

if need_preprocessing:
    # 1. Download CSPEC / Poshist if raw data folder is empty
    cspec_files = os.listdir(cspec_dir) if os.path.exists(cspec_dir) else []
    if len(cspec_files) == 0:
        logging.info("Downloading raw CSPEC and Poshist data...")
        df_days = download_spec(start_month, end_month)
    else:
        logging.info(f"Raw data found in {cspec_dir}. Skipping download.")
        # Reconstruct df_days from existing dates
        days_list = sorted(list(set([f.split('_')[2][:6] for f in cspec_files if f.startswith('glg_cspec')])))
        df_days = pd.DataFrame({"id": days_list, "day": days_list}, index=days_list)

    # 2. Build background CSV tables if not already generated
    bkg_files = [f for f in os.listdir(bkg_dir) if f.endswith('.csv')] if os.path.exists(bkg_dir) else []
    if len(bkg_files) == 0:
        logging.info("Building feature tables from raw data...")
        build_table(df_days, erange, bool_parallel=True, n_jobs=20)
    else:
        logging.info(f"Preprocessed CSV tables found in {bkg_dir}. Skipping build_table.")
else:
    logging.info(f"Prediction file '{pred_file}' already exists. Skipping Download and Preprocessing.")

# ---------------------------------------------------------
# GPU Setup & Hardware Allocation
# ---------------------------------------------------------
import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    logging.info(f"GPU device detected: {gpus[0].name}")
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
            logging.info(f"Memory growth dynamically enabled for {gpu.name}")
        except RuntimeError as e:
            logging.warning(f"Failed setting memory growth: {e}")
else:
    logging.warning("No GPU device detected. Falling back to CPU.")

# ---------------------------------------------------------
# Step 3: Neural Network Model (Train & Predict with cache)
# ---------------------------------------------------------
if not (os.path.isfile(pred_file) and os.path.getsize(pred_file) > 0):
    logging.info("Initializing ModelNN...")
    nn = ModelNN(start_month, end_month)
    
    logging.info("Preparing datasets (sliding windows and normalizations)...")
    nn.prepare(bool_del_trig=True)

    # Check if weights/model already exist in data/nn_model
    valid_extensions = ('.keras', '.h5', '.index')
    saved_models = [
        f for f in os.listdir(nn_model_path)
        if f.endswith(valid_extensions) or os.path.isdir(os.path.join(nn_model_path, f))
    ] if os.path.isdir(nn_model_path) else []

    if len(saved_models) > 0:
        logging.info(f"Trained model found in {nn_model_path} ({saved_models[0]}). Skipping training.")
        train_flag = False
    else:
        logging.info("No trained model found. Starting training on GPU...")
        train_flag = True

    nn.train(
        bool_train=train_flag,
        bool_hyper=False,
        loss_type='mean',
        units=2048,
        epochs=64,
        lr=0.0008,
        bs=8192,
        do=0.02,
        modelcheck=True
    )

    logging.info("Predicting background and writing output tables...")
    nn.predict(time_to_del=150)

    # Diagnostic Plot Generation
    try:
        plt.figure(figsize=(14, 6))
        time_r = slice(10000, 20000)
        det_rng = 'n6_r1'

        # Fallback to test dataframe if df_ori attribute is missing in ModelNN
        df_source = getattr(nn, 'df_ori', getattr(nn, 'df_data', None))
        
        if df_source is not None and hasattr(nn, 'y_pred'):
            x_time = df_source.loc[time_r, 'timestamp'].values
            plt.plot(x_time, df_source.loc[time_r, det_rng].values, label='Observed Count Rate', color='black', alpha=0.5)
            plt.plot(x_time, nn.y_pred.loc[time_r, det_rng].values, label='NN Background Prediction', color='red', linewidth=1.2)
            plt.title(f'DeepGRB - Background Fit ({det_rng})')
            plt.xlabel('Timestamp (MET)')
            plt.ylabel('Counts')
            plt.legend()
            plt.grid(True)
            plot_save_path = os.path.join(plots_dir, 'bkg_orbit_plot.png')
            plt.savefig(plot_save_path, dpi=200, bbox_inches='tight')
            plt.close()
            logging.info(f"Diagnostic plot successfully saved to {plot_save_path}")
        else:
            logging.warning("Dataframes for plotting are unavailable. Skipped Plot 1.")
    except Exception as e:
        logging.warning(f"Could not generate Plot 1: {e}")

else:
    logging.info(f"Using cached background predictions from: {pred_file}")

# ---------------------------------------------------------
# Step 4: Run Trigger (Poisson-FOCuS and Classification)
# ---------------------------------------------------------
logging.info("Adding Fermi GBM trigger catalogs to foreground predictions...")
add_trig_gbm_to_frg(start_month, end_month)

logging.info("Configuring Poisson-FOCuS anomaly detection algorithm...")
trigger_algorithm = focus.set(mu_min=1.2, t_max=50)

logging.info("Running trigger detection...")
run_trigger(start_month, end_month, trigger_algorithm)

bln_update_tables = False
if bln_update_tables:
    logging.info("Updating burst and trigger catalog cache...")
    df_burst_catalog()
    df_trigger_catalog()

logging.info("Running event analysis and post-processing...")
analyze(start_month, end_month, threshold=3., type_time='t90', type_counts='flux')

# ---------------------------------------------------------
# Step 5: Localize Events
# ---------------------------------------------------------
logging.info("Running event localization...")
localize(start_month, end_month)

logging.info("Pipeline execution completed successfully.")