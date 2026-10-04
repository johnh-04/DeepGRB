import logging
from typing import Tuple, List, Dict, Any, Optional

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import matplotlib.transforms as transforms
from pyswarms.single.global_best import GlobalBestPSO
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class Localization:
    """
    Localizza la sorgente di un evento transient (RA, Dec) confrontando i conteggi 
    osservati nei vari rivelatori NaI con la loro risposta geometrica angolare (legge del coseno).
    """

    def __init__(
        self,
        list_ra: np.ndarray,
        list_dec: np.ndarray,
        counts_frg: np.ndarray,
        counts_bkg: np.ndarray
    ) -> None:
        """
        :param list_ra: Array di coordinate RA dei puntamenti dei rivelatori (in radianti)
        :param list_dec: Array di coordinate Dec dei puntamenti dei rivelatori (in radianti)
        :param counts_frg: Conteggi osservati nel foreground
        :param counts_bkg: Conteggi stimati per il background
        """
        self.list_ra = np.asarray(list_ra, dtype=np.float64)
        self.list_dec = np.asarray(list_dec, dtype=np.float64)
        self.counts_frg = np.asarray(counts_frg, dtype=np.float64)
        self.counts_bkg = np.asarray(counts_bkg, dtype=np.float64)
        
        # Segnale netto attribuibile alla sorgente (taglio a zero per fluttuazioni negative)
        self.counts = np.maximum(self.counts_frg - self.counts_bkg, 0.0)
        self.res: Optional[np.ndarray] = None
        self.list_pos: Optional[np.ndarray] = None

        if not (self.list_ra.shape[0] == self.list_dec.shape[0] == self.counts_bkg.shape[0] == self.counts_frg.shape[0]):
            raise ValueError(
                f"Dimension mismatch in input arrays: RA={self.list_ra.shape[0]}, "
                f"Dec={self.list_dec.shape[0]}, Bkg={self.counts_bkg.shape[0]}, Frg={self.counts_frg.shape[0]}"
            )
        self.dim = self.list_ra.shape[0]

    @staticmethod
    def vect_cos(a: Tuple[Any, Any], b: Tuple[Any, Any]) -> np.ndarray:
        """
        Calcola il coseno dell'angolo tra due vettori celesti a=(ra_a, dec_a) e b=(ra_b, dec_b).
        Taglia a zero valori negativi (rivelatori che non vedono la sorgente perché opposti).
        """
        cos_theta = (
            np.cos(a[0]) * np.cos(a[1]) * np.cos(b[0]) * np.cos(b[1]) +
            np.sin(a[0]) * np.cos(a[1]) * np.sin(b[0]) * np.cos(b[1]) +
            np.sin(a[1]) * np.sin(b[1])
        )
        return np.maximum(cos_theta, 0.0)

    def loss_position(self, data: List[Tuple[float, float, float]], x: np.ndarray) -> np.ndarray:
        """
        Funzione di costo quadratica per PSO: confronta i conteggi target con quelli teorici scalati.
        """
        ra = x[:, 0]
        dec = x[:, 1]
        amplitude = x[:, 2]
        
        total_loss = np.zeros(x.shape[0])
        for row in data:
            target_counts = row[2]
            det_pointing = (row[0], row[1])
            expected_counts = amplitude * self.vect_cos((ra, dec), det_pointing)
            total_loss += (expected_counts - target_counts) ** 2
        return total_loss

    def _fit_core(self, list_ra: np.ndarray, list_dec: np.ndarray, counts: np.ndarray, iters: int = 1000) -> Dict[str, float]:
        """Esegue il Particle Swarm Optimization su una singola istanza di conteggi."""
        min_c = float(np.min(counts))
        max_c = float(np.max(counts)) * 2.0
        
        bounds = (
            np.array([0.0, -np.pi / 2.0, min_c]),
            np.array([2.0 * np.pi, np.pi / 2.0, max(max_c, min_c + 1.0)])
        )
        options = {'c1': 0.5, 'c2': 0.3, 'w': 0.9}
        optimizer = GlobalBestPSO(n_particles=100, dimensions=3, options=options, bounds=bounds)
        data = list(zip(list_ra, list_dec, counts))

        def loss_func(x):
            return self.loss_position(data, x)

        _, pos = optimizer.optimize(loss_func, iters=iters, verbose=False)
        return {'ra': pos[0], 'dec': pos[1], 'res_counts': pos[2]}

    def fit(self, iters: int = 1000) -> Dict[str, float]:
        """
        Esegue il fitting PSO globale su tutte le dimensioni temporali/canali.
        Sostituito il vecchio DataFrame.append con accumulo in lista.
        """
        records = []
        for i in range(self.dim):
            rec = self._fit_core(self.list_ra[i], self.list_dec[i], self.counts[i], iters=iters)
            records.append(rec)
            
        df_pos = pd.DataFrame(records)
        self.res = df_pos[['ra', 'dec', 'res_counts']].median().values
        self.list_pos = df_pos[['ra', 'dec']].values

        return {
            'ra': float(self.res[0] / np.pi * 180.0),
            'dec': float(self.res[1] / np.pi * 180.0),
            'res_counts': float(self.res[2])
        }

    def fit_conf_int(self, iters: int = 1000) -> Optional[np.ndarray]:
        """
        Esegue il campionamento Monte Carlo (perturbazioni Poissoniane) per calcolare
        l'ellisse di confidenza della posizione.
        """
        if self.dim > 1:
            logger.info("Already computed for multi-step data. Skipping single confidence interval.")
            return None

        if self.res is None:
            raise RuntimeError("Run fit() before computing confidence intervals.")

        x0 = self.res
        np.random.seed(42)
        list_pos = []
        
        frg_mean = np.maximum(self.counts_frg[0].astype(int), 0)
        bkg_mean = np.maximum(self.counts_bkg[0].astype(int), 0)
        det_ra = self.list_ra[0]
        det_dec = self.list_dec[0]

        for i in range(iters):
            # Campionamento Poissoniano dei conteggi osservati
            sampled_frg = np.random.poisson(frg_mean)
            sampled_bkg = np.random.poisson(bkg_mean)
            counts = np.maximum(sampled_frg - sampled_bkg, 0.0)
            data = list(zip(det_ra, det_dec, counts))

            def loss_position_singular(x):
                ra, dec, amp = x[0], x[1], x[2]
                f = 0.0
                for r in data:
                    cos_val = np.maximum(
                        np.cos(ra) * np.cos(dec) * np.cos(r[0]) * np.cos(r[1]) +
                        np.sin(ra) * np.cos(dec) * np.sin(r[0]) * np.cos(r[1]) +
                        np.sin(dec) * np.sin(r[1]),
                        0.0
                    )
                    f += (amp * cos_val - r[2]) ** 2
                return f

            bounds = ((0.0, 2.0 * np.pi), (-np.pi / 2.0, np.pi / 2.0), (float(np.min(counts)), float(np.max(counts)) * 2.0 + 1.0))
            res = minimize(
                loss_position_singular,
                x0,
                method='L-BFGS-B',
                bounds=bounds,
                options={'gtol': 1e-6, 'disp': False}
            )
            list_pos.append(res.x[0:2])

        self.list_pos = np.array(list_pos)
        return self.list_pos

    def plot(
        self,
        plot_show: bool = False,
        save_path: Optional[str] = None,
        ori_pos: Tuple[Optional[float], Optional[float]] = (None, None),
        n_std: float = 1.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcola matrice di covarianza ed ellisse di errore; supporta salvataggio headless.
        """
        if self.list_pos is None:
            raise RuntimeError("No position list available. Run fit() or fit_conf_int() first.")

        def confidence_ellipse(x, y, ax, n_std_val=3.0, facecolor='none', **kwargs):
            if x.size != y.size:
                raise ValueError("x and y must be the same size")
            cov_mat = np.cov(x, y)
            denom = np.sqrt(cov_mat[0, 0] * cov_mat[1, 1])
            pearson = cov_mat[0, 1] / denom if denom > 0 else 0.0
            
            ell_radius_x = np.sqrt(np.maximum(1.0 + pearson, 0.0))
            ell_radius_y = np.sqrt(np.maximum(1.0 - pearson, 0.0))
            ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2, facecolor=facecolor, **kwargs)

            scale_x = np.sqrt(cov_mat[0, 0]) * n_std_val
            scale_y = np.sqrt(cov_mat[1, 1]) * n_std_val
            mean_x = np.mean(x)
            mean_y = np.mean(y)

            transf = transforms.Affine2D().rotate_deg(45).scale(scale_x, scale_y).translate(mean_x, mean_y)
            ellipse.set_transform(transf + ax.transData)
            return ax.add_patch(ellipse)

        pos_deg = np.array(self.list_pos) / np.pi * 180.0
        mean = np.mean(pos_deg, axis=0)
        cov = np.cov(pos_deg, rowvar=False)

        if plot_show or save_path:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.scatter(pos_deg[:, 0], pos_deg[:, 1], s=1.0, alpha=0.3, label="Monte Carlo Samples")
            confidence_ellipse(pos_deg[:, 0], pos_deg[:, 1], ax, n_std_val=n_std, edgecolor='red', label=f'{n_std}-sigma Ellipse')
            
            if self.res is not None:
                ax.scatter(self.res[0] * 180.0 / np.pi, self.res[1] * 180.0 / np.pi, c='green', marker='*', s=60, label="Best Fit (PSO)")
            ax.scatter(mean[0], mean[1], c='red', marker='+', s=50, label="Sample Mean")
            
            if ori_pos[0] is not None and ori_pos[1] is not None:
                ax.scatter(ori_pos[0], ori_pos[1], c='black', marker='x', s=50, label="Catalog True Position")

            ax.set_xlabel("Right Ascension (deg)")
            ax.set_ylabel("Declination (deg)")
            ax.legend(loc="best")
            ax.grid(True, linestyle="--", alpha=0.5)

            if save_path:
                plt.savefig(save_path, bbox_inches="tight", dpi=150)
                logger.info(f"Localization plot saved to: {save_path}")
            
            if plot_show:
                plt.show()
            plt.close(fig)

        return mean, cov