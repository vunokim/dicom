import os
import pydicom
from datetime import datetime, timedelta
from collections import defaultdict

import pandas as pd

# CSV 불러오기
csv_path = "D:\\chestxray_sample\\kaggle\\NIH_Chest_X-rays_Pneumothorax\\Pneumothorax.csv"
df = pd.read_csv(csv_path)

# Study UID를 Patient ID별로 고정시키기 위한 딕셔너리
study_uid_map = defaultdict(lambda: pydicom.uid.generate_uid())

# 기준 날짜
base_date = datetime(2021, 1, 6)

# 수정할 DICOM 폴더 경로
dicom_dir = "D:\\chestxray_sample\\kaggle\\NIH_Chest_X-rays_Pneumothorax\\dcm"  # <-- 여기에 실제 DICOM 폴더 경로 입력

for _, row in df.iterrows():
    filename = row['Image Index']
    dcm_path = os.path.join(dicom_dir, filename)

    if not os.path.exists(dcm_path):
        print(f"파일 없음: {filename}")
        continue

    ds = pydicom.dcmread(dcm_path)

    # 1. Patient ID
    patient_id_str = str(row['Image Index']).split('_')[0]
    ds.PatientID = patient_id_str

    # 2. Patient's Sex
    ds.PatientSex = row['Patient Gender']

    # 3. Patient's Age (형식: 060Y)
    age_str = str(row['Patient Age']).zfill(3) + 'Y'
    ds.PatientAge = age_str

    # 4. Patient's Birth Date (기준 날짜에서 나이만큼 빼기)
    birth_year = base_date.year - int(row['Patient Age'])
    birth_date = datetime(birth_year, base_date.month, base_date.day)
    ds.PatientBirthDate = birth_date.strftime('%Y%m%d')

    # 5. Study Date & Series Date
    ds.StudyDate = '20210116'
    ds.SeriesDate = '20210116'

    # 6. Study Description & Series Description
    desc = f"Chest {row['View Position']}, Lateral"
    ds.StudyDescription = desc
    ds.SeriesDescription = desc

    # 7. View Position
    ds.ViewPosition = row['View Position']

    # 8. Study Instance UID (환자 기준 고정), Series Number (Follow-up #)
    patient_uid = study_uid_map[ds.PatientID]
    ds.StudyInstanceUID = patient_uid
    ds.SeriesNumber = int(row['Follow-up #'])

    # 9. Image Index 기준 파일명 매칭은 위에서 처리됨

    # 10. Modality
    ds.Modality = 'CR'

    # 11. 태그가 없다면 생성하여 삽입 → 위에서 이미 할당 시 생성됨

    # 12. Medical Alerts: Finding Labels를 | → , 로 바꿔서 넣기
    findings = str(row['Finding Labels']).replace('|', ', ')

    # 13. Patient's Name ← 확장자 제거한 파일명
    ds.PatientName = os.path.splitext(filename)[0]
    ds.MedicalAlerts = findings

    # 저장
    ds.save_as(dcm_path)
    print(f"수정 완료: {filename}")
