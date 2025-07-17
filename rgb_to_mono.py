import os
import pydicom
import numpy as np
from PIL import Image

def convert_rgb_to_monochrome2(dcm_path, output_path):
    ds = pydicom.dcmread(dcm_path)

    # RGB 픽셀 데이터를 numpy array로 변환
    pixel_array = ds.pixel_array  # shape: (H, W, 3)

    if len(pixel_array.shape) == 3 and pixel_array.shape[2] == 3:
        # RGB → 그레이스케일 (luminosity method)
        gray = np.dot(pixel_array[...,:3], [0.2989, 0.5870, 0.1140]).astype(np.uint8)

        # DICOM 데이터 수정
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.SamplesPerPixel = 1
        ds.PlanarConfiguration = None
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        ds.PixelData = gray.tobytes()

        ds.Rows, ds.Columns = gray.shape
        ds.save_as(output_path)
        print(f"변환 완료: {output_path}")
    else:
        print(f"RGB 이미지가 아님: {dcm_path}")

# 폴더 내 모든 DICOM 처리
input_folder = "D:\\chestxray_sample\\kaggle\\PneumothoraxMasks\\siim-acr-pneumothorax\\test\\111"
output_folder = "D:\\chestxray_sample\\kaggle\\PneumothoraxMasks\\siim-acr-pneumothorax\\test\\111\\out"
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.endswith(".dcm"):
        convert_rgb_to_monochrome2(
            os.path.join(input_folder, filename),
            os.path.join(output_folder, filename)
        )
