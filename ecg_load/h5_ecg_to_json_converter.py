<<<<<<< HEAD
import os
import h5py
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from scipy.signal import butter, filtfilt


def bandpass_filter(signal, lowcut, highcut, fs, order=3):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal, axis=0)


def load_ecg_from_hdf5(file_path):
    with h5py.File(file_path, 'r') as f:
        ecg = f['ecg'][:]  # (12, N) 형태
    ecg = ecg.T  # (N, 12)
    fs = 500  # Hz
    return ecg, fs


def create_json(file_path, ecg_data, fs, lead_names):
    json_obj = {
        "patient_id": os.path.splitext(os.path.basename(file_path))[0],
        "measure_time": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "samplerate": float(fs),
        "leads": {}
    }

    for i, lead in enumerate(lead_names):
        json_obj["leads"][lead] = [round(float(v), 5) for v in ecg_data[:, i]]

    return json_obj


def convert_h5_to_json(h5_path, output_dir, lead_names):
    ecg, fs = load_ecg_from_hdf5(h5_path)
    ecg_filtered = bandpass_filter(ecg, 0.5, 40, fs)

    json_data = create_json(h5_path, ecg_filtered, fs, lead_names)

    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, os.path.splitext(os.path.basename(h5_path))[0] + ".json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 변환 완료: {os.path.basename(json_path)}")
    return json_path


def batch_convert_h5_folder(input_dir, output_dir):
    lead_names = ['I', 'II', 'III', 'AVR', 'AVL', 'AVF',
                  'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

    os.makedirs(output_dir, exist_ok=True)
    h5_files = [f for f in os.listdir(input_dir) if f.endswith('.h5')]

    for file_name in sorted(h5_files):
        file_path = os.path.join(input_dir, file_name)
        try:
            convert_h5_to_json(file_path, output_dir, lead_names)
        except Exception as e:
            print(f"❌ 변환 실패: {file_name} → {e}")


# 예시 실행
if __name__ == '__main__':
    input_directory = 'D:\\ECG\\12leads_AHA_standard\\records'    # .h5 파일이 들어있는 폴더 경로
    output_directory = 'D:\\ECG\\12leads_AHA_standard\\json'  # 결과 .json 저장 폴더
    batch_convert_h5_folder(input_directory, output_directory)
=======
import os
import h5py
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from scipy.signal import butter, filtfilt


def bandpass_filter(signal, lowcut, highcut, fs, order=3):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal, axis=0)


def load_ecg_from_hdf5(file_path):
    with h5py.File(file_path, 'r') as f:
        ecg = f['ecg'][:]  # (12, N) 형태
    ecg = ecg.T  # (N, 12)
    fs = 500  # Hz
    return ecg, fs


def create_json(file_path, ecg_data, fs, lead_names):
    json_obj = {
        "patient_id": os.path.splitext(os.path.basename(file_path))[0],
        "measure_time": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "samplerate": float(fs),
        "leads": {}
    }

    for i, lead in enumerate(lead_names):
        json_obj["leads"][lead] = [round(float(v), 5) for v in ecg_data[:, i]]

    return json_obj


def convert_h5_to_json(h5_path, output_dir, lead_names):
    ecg, fs = load_ecg_from_hdf5(h5_path)
    ecg_filtered = bandpass_filter(ecg, 0.5, 40, fs)

    json_data = create_json(h5_path, ecg_filtered, fs, lead_names)

    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, os.path.splitext(os.path.basename(h5_path))[0] + ".json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 변환 완료: {os.path.basename(json_path)}")
    return json_path


def batch_convert_h5_folder(input_dir, output_dir):
    lead_names = ['I', 'II', 'III', 'AVR', 'AVL', 'AVF',
                  'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

    os.makedirs(output_dir, exist_ok=True)
    h5_files = [f for f in os.listdir(input_dir) if f.endswith('.h5')]

    for file_name in sorted(h5_files):
        file_path = os.path.join(input_dir, file_name)
        try:
            convert_h5_to_json(file_path, output_dir, lead_names)
        except Exception as e:
            print(f"❌ 변환 실패: {file_name} → {e}")


# 예시 실행
if __name__ == '__main__':
    input_directory = 'D:\\ECG\\12leads_AHA_standard\\records'    # .h5 파일이 들어있는 폴더 경로
    output_directory = 'D:\\ECG\\12leads_AHA_standard\\json'  # 결과 .json 저장 폴더
    batch_convert_h5_folder(input_directory, output_directory)
>>>>>>> 0eb1d258402411ad34ee3ac09ddb137e034d4ea3
