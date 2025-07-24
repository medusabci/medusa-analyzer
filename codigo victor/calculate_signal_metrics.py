import numpy as np
import pickle
from medusa import signal_metrics
from medusa import transforms
from scipy.signal import welch


bands = [
    np.array([1, 4]),    # Delta
    np.array([4, 8]),      # Theta
    np.array([8, 13]),     # Alpha
    np.array([13, 19]),    # Beta1
    np.array([19, 30]),   # Beta2
    np.array([30, 70]),   # Gamma
    np.array([1, 70])
]
norm_band = (1,70)

def calculate_signal_metrics(signal, fs, params):
    """
   Function that calculates the signal parameters in "param" of the signals in "signal"

   Args:
        data : numpy.ndarray
            M/EEG signal. Accepted shapes:
            - [n_epochs, n_samples, n_channels]
            - [n_samples, n_channels] (interpreted as one epoch)
        params (list): list of parameters to be calculated
            Accepted values: 'MF','IAF','SE','RP','LZC','CTM','SampEn','MSE','MSLZC'

   Returns:
       param_values: list: list of the calculated signal paramaters

   """
    # Variable initialization
    param_data = {}
    param_data['params_data'] = []
    param_data['labels'] = signal['epoch_labels']

    # Loop that calculate the parameters
    for n_group_of_trial, group_of_trial in enumerate(signal['epoched_signals']):
        # Initilize the variables
        param_data_tmp = {}

        # Get the current signal and compute its PSD
        fxx, current_signal_psd = welch(group_of_trial, fs=fs, window='hann', nfft=2048, return_onesided=True, axis=1)
        current_signal_psd_norm = transforms.normalize_psd(current_signal_psd, band=bands[-1], fxx=fxx)

        # Compute the parameters
        for param in params:
            if param == 'MF':
                tmp_value = signal_metrics.median_frequency(current_signal_psd, fs)
            elif param == 'IAF':
                tmp_value = signal_metrics.median_frequency(current_signal_psd, fs, target_band=(4,15))
            elif param == 'SE':
                tmp_value = []
                for n_band, band in enumerate(bands):
                    tmp_value.append(signal_metrics.shannon_spectral_entropy(current_signal_psd, fs, target_band=band))
                tmp_value = np.moveaxis(np.array(tmp_value),[0,1],[1,0])
            elif param == 'RP':
                tmp_value = []
                for n_band, band in enumerate(bands[:-1]):
                    tmp_value.append(signal_metrics.band_power(current_signal_psd_norm, fs, target_band=band, apply_bin_norm=False))
                tmp_value = np.moveaxis(np.array(tmp_value),[0,1],[1,0])
            elif param == 'LZC':
                tmp_value = signal_metrics.lempelziv_complexity(group_of_trial[:2,:,:])
            elif param == 'CTM':
                tmp_value = signal_metrics.central_tendency_measure(group_of_trial, r=0.075)
            elif param == 'SampEn':
                tmp_value = signal_metrics.sample_entropy(group_of_trial, m=1, r=0.25)
            elif param == 'MSE':
                tmp_value = signal_metrics.multiscale_entropy(group_of_trial, max_scale=20, m=1, r=0.25)
            elif param == 'MSLZC':
                tmp_value = signal_metrics.multiscale_lempelziv_complexity(group_of_trial, W=[3,5,11,25,55])

            param_data_tmp[param] = np.array(tmp_value)
            del tmp_value
        del group_of_trial, current_signal_psd

        param_data['params_data'].append(param_data_tmp)
        del param_data_tmp
    return param_data

if __name__ == '__main__':

    with open('signal.pkl', 'rb') as f:
        signal = pickle.load(f)

    holaaa = calculate_signal_metrics(signal, 250, ['MF','IAF','SE','RP','LZC','CTM','SampEn','MSE','MSLZC'])
    a = 0