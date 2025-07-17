import h5py
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt


def bandpass_filter(signal, lowcut, highcut, fs, order=3):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal, axis=0)


def load_ecg_from_hdf5(file_path):
    with h5py.File(file_path, 'r') as f:
        ecg = f['ecg'][:]  # shape: (12, 5000)
    ecg = ecg.T  # shape: (5000, 12)
    fs = 500  # 샘플링 주파수 (Hz)
    return ecg, fs


def plot_ecg_grid(ecg, fs, layout_order, lead_mapping):
    short_duration = int(2.5 * fs)
    long_duration = int(10 * fs)

    fig = plt.figure(figsize=(16, 12))
    sec_per_mm = 0.04
    mv_per_mm = 0.1

    lead_indices = {name: i for i, name in enumerate(lead_mapping)}

    for i, lead in enumerate(layout_order):
        ax = fig.add_subplot(4, 4, i + 1)
        idx = lead_indices[lead]
        data = ecg[:short_duration, idx]
        time = np.arange(len(data)) / fs
        ax.plot(time, data, linewidth=0.8, color='blue')

        ax.set_xlim(0, 2.5)
        ax.set_ylim(-2, 2)
        ax.set_xticks(np.arange(0, 2.6, 0.2))
        ax.set_yticks(np.arange(-2.0, 2.1, 0.5))
        ax.set_xticks(np.arange(0, 2.6, sec_per_mm), minor=True)
        ax.set_yticks(np.arange(-2.0, 2.1, mv_per_mm), minor=True)
        ax.grid(True, which='major', linestyle='--', linewidth=0.5)
        ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='gray')

        ax.set_title(lead, fontsize=10)
        ax.tick_params(labelsize=6)
        ax.set_xlabel("Time (s)", fontsize=7)
        ax.set_ylabel("Amplitude (mV)", fontsize=7)

    ax = fig.add_subplot(4, 1, 4)
    idx = lead_indices['II']
    data = ecg[:long_duration, idx]
    time = np.arange(len(data)) / fs
    ax.plot(time, data, linewidth=0.8, color='blue')
    ax.set_title("II (repeat)", fontsize=10)

    ax.set_xlim(0, 10)
    ax.set_ylim(-2, 2)
    ax.set_xticks(np.arange(0, 10.1, 0.2))
    ax.set_yticks(np.arange(-2.0, 2.1, 0.5))
    ax.set_xticks(np.arange(0, 10.1, sec_per_mm), minor=True)
    ax.set_yticks(np.arange(-2.0, 2.1, mv_per_mm), minor=True)
    ax.grid(True, which='major', linestyle='--', linewidth=0.5)
    ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='gray')
    ax.tick_params(labelsize=6)
    ax.set_xlabel("Time (s)", fontsize=7)
    ax.set_ylabel("Amplitude (mV)", fontsize=7)

    fig.subplots_adjust(hspace=0.9, top=0.95)
    return fig


if __name__ == '__main__':
    file_path = 'D:\\ECG\\12leads_AHA_standard\\records\\A00001.h5'
    ecg, fs = load_ecg_from_hdf5(file_path)
    ecg = bandpass_filter(ecg, 0.5, 40, fs)

    layout_order = ['I', 'aVR', 'V1', 'V4',
                    'II', 'aVL', 'V2', 'V5',
                    'III', 'aVF', 'V3', 'V6']

    lead_mapping = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
                    'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

    fig = plot_ecg_grid(ecg, fs, layout_order, lead_mapping)
    fig.savefig("final_ecg_layout.png", dpi=150)
    plt.show()
