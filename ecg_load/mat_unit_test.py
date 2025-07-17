import os
import numpy as np
from scipy.io import loadmat
import wfdb

def classify_unit(mat_path, hea_path):
    try:
        # 1. Load signal
        mat_data = loadmat(mat_path)
        signal = mat_data['val'].T  # shape: (samples, leads)
        lead_0 = signal[:, 0]

        # 2. Load gain from header
        base_path = os.path.splitext(hea_path)[0]
        header = wfdb.rdheader(base_path)
        gain_vector = header.adc_gain
        gain_0 = gain_vector[0] if gain_vector[0] != 0 else 200

        # 3. Normalize in two ways
        mv_by_200 = lead_0 / gain_0
        mv_by_1000 = lead_0 / 1000.0

        max_200 = np.max(np.abs(mv_by_200))
        max_1000 = np.max(np.abs(mv_by_1000))

        # 4. Decision logic
        def is_valid_range(val):  # acceptable mV range
            return 0.5 < val < 3.0

        if is_valid_range(max_200) and not is_valid_range(max_1000):
            return "200"
        elif is_valid_range(max_1000) and not is_valid_range(max_200):
            return "1000"
        elif is_valid_range(max_200) and is_valid_range(max_1000):
            return "both"
        else:
            return "invalid"
    except Exception as e:
        return f"error: {e}"

def batch_analyze_ecg_folder(folder_path):
    stats = {
        "200": 0,
        "1000": 0,
        "both": 0,
        "invalid": 0,
        "error": 0
    }

    mat_files = [f for f in os.listdir(folder_path) if f.endswith('.mat')]
    mat_files.sort()

    print(f"🔍 총 {len(mat_files)}개의 .mat 파일을 분석합니다...\n")

    for i, mat_file in enumerate(mat_files):
        base = os.path.splitext(mat_file)[0]
        mat_path = os.path.join(folder_path, base + '.mat')
        hea_path = os.path.join(folder_path, base + '.hea')
        if not os.path.exists(hea_path):
            print(f"[{i+1}] {base}: ❌ .hea 파일 없음 → 건너뜀")
            continue

        result = classify_unit(mat_path, hea_path)
        key = result if result in stats else "error"
        stats[key] += 1

        print(f"[{i+1:4}] {base}: ✔ 분류 결과 → {result}")

    # 결과 요약
    print("\n📊 분석 요약")
    print(f"  /200 정규화 적절:   {stats['200']}")
    print(f"  /1000 정규화 적절:  {stats['1000']}")
    print(f"  둘 다 가능:         {stats['both']}")
    print(f"  부적절 or 이상치:   {stats['invalid']}")
    print(f"  오류 발생:          {stats['error']}")
    print(f"  총 분석된 쌍 수:    {sum(stats.values())}")

# 사용 예시
if __name__ == "__main__":
    ecg_folder = "D:\\ECG\\Ischemia_dataset\\ischemia_dataset"  # 여기에 .mat/.hea 파일 폴더 경로 입력
    batch_analyze_ecg_folder(ecg_folder)
