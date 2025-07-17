import os
import pydicom

def modify_dicom_tags_in_folder(folder_path):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".dcm"):
            filepath = os.path.join(folder_path, filename)
            try:
                ds = pydicom.dcmread(filepath)

                # 1. 파일명(확장자 제외)을 Patient ID에 삽입
                patient_id = os.path.splitext(filename)[0]
                ds.PatientID = patient_id

                # 2. Study Date & Series Date
                ds.StudyDate = '20200103'
                ds.SeriesDate = '20200103'

                # 3. Patient's Birth Date
                ds.PatientBirthDate = '19610106'

                # 4. Patient's Age
                ds.PatientAge = '059Y'

                # 덮어쓰기 저장
                ds.save_as(filepath)
                print(f"✅ 수정 완료: {filename}")

            except Exception as e:
                print(f"❌ 오류 발생 ({filename}): {e}")

# 사용 예시
folder_path = "D:\\chestxray_sample\\kaggle\\PneumothoraxMasks\\siim-acr-pneumothorax\\test\\111"
modify_dicom_tags_in_folder(folder_path)
