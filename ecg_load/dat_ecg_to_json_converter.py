import os
import wfdb
import json
from datetime import datetime, timezone, timedelta
from scipy.signal import butter, filtfilt
import numpy as np

def bandpass_filter(signal, lowcut, highcut, fs, order=3):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, signal, axis=0)

def create_json(record_path, record, filtered_signal):
    json_obj = {
        "patient_id": os.path.basename(record_path),
        "measure_time": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "samplerate": float(record.fs),
        "leads": {}
    }

    for i, lead in enumerate(record.sig_name):
        json_obj["leads"][lead] = [round(float(v), 5) for v in filtered_signal[:, i]]

    return json_obj

def convert_to_json(dat_file, hea_file, output_dir):
    try:
        record_path = os.path.splitext(dat_file)[0]
        record = wfdb.rdrecord(record_path)
        filtered = bandpass_filter(record.p_signal, 0.5, 40, record.fs)

        json_data = create_json(record_path, record, filtered)

        output_path = os.path.join(output_dir, os.path.basename(record_path) + '.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        return True, os.path.basename(record_path)
    except Exception as e:
        return False, f"{os.path.basename(dat_file)}: {e}"

def batch_convert(dat_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    all_files = os.listdir(dat_dir)
    dat_files = sorted([f for f in all_files if f.endswith('.dat')])

    for dat in dat_files:
        base = os.path.splitext(dat)[0]
        hea = base + '.hea'
        dat_path = os.path.join(dat_dir, dat)
        hea_path = os.path.join(dat_dir, hea)
        if os.path.exists(hea_path):
            success, msg = convert_to_json(dat_path, hea_path, output_dir)
            if success:
                print(f"변환 성공: {msg}.json")
            else:
                print(f"변환 실패: {msg}")
        else:
            print(f"헤더 파일 누락: {hea}")

if __name__ == '__main__':
    input_dir = 'D:\\ECG\\ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3\\AMI'  # 여기에 .dat/.hea 폴더 경로 입력
    output_dir = 'D:\\ECG\\ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3\\AMI\\json'  # 여기에 결과 저장 폴더 경로 입력
    batch_convert(input_dir, output_dir)
