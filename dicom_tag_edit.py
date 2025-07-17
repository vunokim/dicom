import os
import pandas as pd
import pydicom
from pydicom.uid import generate_uid
import re
from datetime import datetime

# 환자 이름 정리 함수
def sanitize_patient_name(name):
    name = str(name)
    name = name.replace('，', ',')
    name = re.sub(r'[^\w\s,.-]', '-', name)
    name = name.strip()
    return name[:64]

# 기준일 설정
REFERENCE_DATE = datetime(2020, 9, 24)

# 경로 설정
dicom_folder = 'D:\\fundus\\kaggle\\OcularDiseaseRecognition\\ODIR-5K\\ODIR-5K\\Training Images\\dcm'
csv_path = 'D:\\fundus\\kaggle\\OcularDiseaseRecognition\\ODIR-5K\\ODIR-5K\\metadata.csv'

# CSV 읽기
df = pd.read_csv(csv_path)
file_dict = {row['filename']: row for _, row in df.iterrows()}
study_uid_map = {}
series_number_tracker = {}

# DICOM 처리
for fname in os.listdir(dicom_folder):
    if not fname.endswith('.dcm'):
        continue

    filepath = os.path.join(dicom_folder, fname)
    ds = pydicom.dcmread(filepath)

    if fname not in file_dict:
        print(f"CSV에 {fname} 정보 없음. 건너뜀.")
        continue

    row = file_dict[fname]

    # 1. Patient Age
    ds.PatientAge = str(row['Patient Age']).zfill(3) + 'Y'

    # 2. Patient Sex
    ds.PatientSex = row['Patient Sex']

    # 3. Patient Name
    raw_name = row['Diagnostic Keywords']
    ds.PatientName = sanitize_patient_name(raw_name)

    # 4. Patient ID
    ds.PatientID = os.path.splitext(fname)[0]

    # 5. Laterality & Series Description
    if '_left' in fname:
        ds.Laterality = 'L'
        ds.SeriesDescription = 'Color/L'
    elif '_right' in fname:
        ds.Laterality = 'R'
        ds.SeriesDescription = 'Color/R'

    # 6. Study Instance UID
    prefix = fname.replace('_left.dcm', '').replace('_right.dcm', '').replace('.dcm', '')
    if prefix not in study_uid_map:
        study_uid_map[prefix] = generate_uid()
    study_uid = study_uid_map[prefix]
    ds.StudyInstanceUID = study_uid

    # ✅ (0008,0060) Modality = "SC"
    ds.Modality = "SC"

    # ✅ (0010,0030) Patient's Birth Date 계산
    try:
        age = int(row['Patient Age'])
        birth_year = REFERENCE_DATE.year - age
        birth_date = datetime(birth_year, REFERENCE_DATE.month, REFERENCE_DATE.day)
        ds.PatientBirthDate = birth_date.strftime('%Y%m%d')
    except:
        print(f"{fname}: 생년 계산 오류 - Patient Age 값 확인 필요")

    # ✅ (0020,0011) Series Number: 왼쪽 1, 오른쪽 2 번갈아
    if study_uid not in series_number_tracker:
        series_number_tracker[study_uid] = {'left': 0, 'right': 0}
    if '_left' in fname:
        series_number_tracker[study_uid]['left'] += 1
        ds.SeriesNumber = 1
    elif '_right' in fname:
        series_number_tracker[study_uid]['right'] += 1
        ds.SeriesNumber = 2

    # 저장
    ds.save_as(filepath)
    print(f"{fname} 처리 완료.")

print("✅ 모든 DICOM 파일 처리 완료.")
