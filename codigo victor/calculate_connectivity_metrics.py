from medusa import connectivity_metrics
import numpy as np
import pickle

def calculate_connectivity_metrics(signal, params, ort):
    """
   Function that calculates the connectivity parameters in "param" of the signals in "signal"

   Args:
        data : numpy.ndarray
            M/EEG signal. Accepted shapes:
            - [n_epochs, n_samples, n_channels]
            - [n_samples, n_channels] (interpreted as one epoch)
        params (list): list of parameters to be calculated
            Accepted values: 'AEC','IAC','PLI','wPLI','PLV'
        ort (bool):
            Whether to orthogonalize the signal before computing AEC and IAC

   Returns:
       param_values: list: list of the calculated connectivity paramaters

   """
    # Variable initialization
    param_data = {}
    param_data['params_data'] = []
    param_data['labels'] = signal['epoch_labels']

    # Loop that calculate the parameters
    for n_group_of_trial, group_of_trial in enumerate(signal['epoched_signals']):
        # Initilize the variables
        param_data_tmp = {}
        for param in params:
            if param == 'AEC':
                tmp_value = connectivity_metrics.aec(group_of_trial, ort=ort)
            if param == 'IAC':
                tmp_value = connectivity_metrics.iac(group_of_trial, ort=ort)
            if param == 'PLV':
                tmp_value = connectivity_metrics.plv(group_of_trial)
            if param == 'PLI':
                tmp_value = connectivity_metrics.pli(group_of_trial)
            if param == 'wPLI':
                tmp_value = connectivity_metrics.wpli(group_of_trial)

            param_data_tmp[param] = np.array(tmp_value)
            del tmp_value
        del group_of_trial

        param_data['params_data'].append(param_data_tmp)
        del param_data_tmp
    return param_data

if __name__ == '__main__':

    with open('signal.pkl', 'rb') as f:
        signal = pickle.load(f)

    holaaa = calculate_connectivity_metrics(signal, ['AEC', 'IAC', 'PLV', 'PLI', 'wPLI'], True)
    a = 0