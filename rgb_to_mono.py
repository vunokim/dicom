import os
import pydicom
import numpy as np
from pydicom.uid import generate_uid

def convert_rgb_to_monochrome2(dcm_path, output_path):
    ds = pydicom.dcmread(dcm_path)

    # RGB 픽셀 데이터를 numpy array로 변환
    pixel_array = ds.pixel_array  # shape: (H, W, 3)

    if len(pixel_array.shape) == 3 and pixel_array.shape[2] == 3:
        # RGB → Grayscale (luminosity method)
        gray_float = np.dot(pixel_array[...,:3], [0.2989, 0.5870, 0.1140])

        # dtype 판단
        original_dtype = pixel_array.dtype
        print(f"{os.path.basename(dcm_path)}: dtype = {original_dtype}")

        if original_dtype == np.uint8:
            gray = gray_float.astype(np.uint8)
            ds.BitsAllocated = 8
            ds.BitsStored = 8
            ds.HighBit = 7

        elif original_dtype == np.uint16:
            bits_stored = getattr(ds, 'BitsStored', 12)
            if bits_stored > 16 or bits_stored < 1:
                print(f"⚠️ 잘못된 BitsStored 값 감지: {bits_stored}, 12로 설정")
                bits_stored = 12

            max_val = 2**bits_stored - 1
            gray_normalized = gray_float / gray_float.max() * max_val
            gray = gray_normalized.astype(np.uint16)

            ds.BitsAllocated = 16
            ds.BitsStored = bits_stored
            ds.HighBit = bits_stored - 1

        else:
            print(f"❌ 지원되지 않는 dtype: {original_dtype}")
            return

        # DICOM 태그 갱신
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.SamplesPerPixel = 1
        if 'PlanarConfiguration' in ds:
            del ds.PlanarConfiguration
        ds.PixelRepresentation = 0

        # 필수 태그 보정
        ds.ConversionType = "WSD"  # 이미지 변환 방식 명시
        if not hasattr(ds, 'SOPInstanceUID'):
            ds.SOPInstanceUID = generate_uid()

        # 불필요한 태그 제거
        for tag in ["NumberOfFrames", "FrameTime"]:
            if tag in ds:
                delattr(ds, tag)

        # 픽셀 저장
        ds.PixelData = gray.tobytes()
        ds.Rows, ds.Columns = gray.shape

        # 저장
        ds.save_as(output_path, write_like_original=False)
        print(f"✅ 변환 완료: {output_path}")
    else:
        print(f"⚠️ RGB 이미지가 아님: {dcm_path}")

# 폴더 내 모든 DICOM 처리
input_folder = "D:\\chestxray_sample\\kaggle\\PneumothoraxMasks\\siim-acr-pneumothorax\\test\\img"
output_folder = os.path.join(input_folder, "out")
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.lower().endswith(".dcm"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        convert_rgb_to_monochrome2(input_path, output_path)
