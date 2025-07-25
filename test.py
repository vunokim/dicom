import os
import pydicom
from pydicom.tag import Tag

def update_dicom_tags(input_folder, output_folder):
    # 출력 폴더 없으면 생성
    os.makedirs(output_folder, exist_ok=True)

    # 입력 폴더 내 모든 파일 처리
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".dcm"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)

            try:
                ds = pydicom.dcmread(input_path)

                # (0008,0005) Specific Character Set
                ds[Tag(0x0008, 0x0005)] = pydicom.DataElement(
                    Tag(0x0008, 0x0005), 'CS', ['ISO 2022 IR 13', 'ISO 2022 IR 87', 'ISO 2022 IR 100']
                )

                # (0010,0010) Patient's Name
                ds[Tag(0x0010, 0x0010)] = pydicom.DataElement(
                    Tag(0x0010, 0x0010), 'PN', 'AKIHABARA^TARO=秋葉原^太郎=あきはばら^たろう'
                )

                # 저장
                ds.save_as(output_path)
                print(f"[✔] Updated: {filename}")

            except Exception as e:
                print(f"[✘] Failed: {filename} - {e}")

# 사용 예
update_dicom_tags("D:\\chestxray_sample\\assist_jpn\\pacs\\aaa", "D:\\chestxray_sample\\assist_jpn\\pacs\\aaa\\out")
