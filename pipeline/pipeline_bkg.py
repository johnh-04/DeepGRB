# import packages
from connections.fermi_data_tools import df_burst_catalog, df_trigger_catalog
from models.download_bkg import download_spec
from models.preprocess import build_table
from models.model_nn import ModelNN
from models.trigger import run_trigger
from models.trigs import focus
from models.analyze import analyze
from models.utils.GBMutils import add_trig_gbm_to_frg
from models.localize_event import localize
import logging
import os
import matplotlib
matplotlib.use('Agg')  # headless mode to save plots
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

# Define range of energy
erange = {'n': [(28, 50), (50, 300), (300, 500)], 'b': [(756, 5025), (5025, 50000)]}
start_month = "03-2019"
end_month = "07-2019"

# 1 Download CSPEC and Poshist
df_days = download_spec(start_month, end_month)

# Test to download only one week
# import pandas as pd
# days_list = [f"19030{i}" for i in range(1, 8)]
# df_days = pd.DataFrame({"id": days_list, "day": days_list}, index=days_list)

# 2 Elaborate CSPEC and Poshist -> to csv
build_table(df_days, erange, bool_parallel=True, n_jobs=20)

import tensorflow as tf

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f"GPU found: {gpus[0]}")
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
else:
    print("GPU not found, building on CPU")

# 3 Train NN
nn = ModelNN(start_month, end_month)
nn.prepare(bool_del_trig=True)
nn.train(bool_train=False, bool_hyper=False, loss_type='mean', units=2048, epochs=64, lr=0.0008, bs=2048, do=0.02, modelcheck=True)
nn.predict(time_to_del=150)  # set to 150 by default

# Plot folders
os.makedirs('/lustrehome/gpm04/DeepGRB/data/plots', exist_ok=True)

# Plot 1: Orbit / Background Prediction
try:
    plt.figure(figsize=(14, 6))
    time_r = slice(10000, 20000)
    det_rng = 'n6_r1'
    x_time = nn.df_ori.loc[time_r, 'timestamp'].values
    plt.plot(x_time, nn.df_ori.loc[time_r, det_rng].values, label='Osservato (df_ori)', color='black', alpha=0.5)
    plt.plot(x_time, nn.y_pred.loc[time_r, det_rng].values, label='Predizione Bkg (NN)', color='red', linewidth=1.2)
    plt.title(f'DeepGRB - Fondo stimato ({det_rng})')
    plt.xlabel('Timestamp')
    plt.ylabel('Counts')
    plt.legend()
    plt.grid(True)
    plt.savefig('/lustrehome/gpm04/DeepGRB/data/plots/bkg_orbit_plot.png', dpi=200, bbox_inches='tight')
    plt.close()
    logging.info("Plot 1 salvato in data/plots/bkg_orbit_plot.png")
except Exception as e:
    logging.warning(f"Salvataggio Plot 1 non riuscito: {e}")

# Interactive methods that cause crashes on headless server
# nn.plot(time_r=range(10000, 200000), orbit_bin=1, det_rng='n6_r1')
# nn.plot(time_r=(-1000, 1000), time_iso='2019-03-04T13:08:00', det_rng='n6_r0')
# nn.explain(time_r=range(0, 10))

# 4 Run trigger (bkg, frg)
add_trig_gbm_to_frg(start_month, end_month)
trigger_algorithm = focus.set(mu_min=1.2, t_max=50)
run_trigger(start_month, end_month, trigger_algorithm)
bln_update_tables = False
if bln_update_tables:
    df_burst_catalog()
    df_trigger_catalog()
analyze(start_month, end_month, threshold=3., type_time='t90', type_counts='flux')

# 5 Localise events
localize(start_month, end_month)
pass