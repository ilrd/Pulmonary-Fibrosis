import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from pandas.plotting import scatter_matrix
import pydicom as dicom
import os
from collections import defaultdict
from time import perf_counter, sleep
import gc
from PIL import Image
import PIL

# Plan
'''
1. Preprocess DICOM images - Done
2. Turn DICOM to numpy arrays - Done
3. Preprocess CSVs
4. Save the processed data
'''

project_dir = '/home/ilolio/PycharmProjects/Kaggle-Pulmonary-Fibrosis'


def crop_image(img, tol=0):
    # img is 2D image data
    # tol  is tolerance
    mask = img != img[0, 0]

    ix = np.ix_(mask.any(1), mask.any(0))
    return img[ix]


def show_window(ct_img, w=None, m=None):
    ct_img = ct_img.copy()
    if w and m:
        l_bound = int(m - w / 2)
        r_bound = int(m + w / 2)
        ct_img[ct_img < l_bound] = l_bound
        ct_img[ct_img > r_bound] = r_bound
    else:
        w = abs(ct_img.min()) + ct_img.max()
        m = w / 2

    plt.figure(figsize=(9, 9))
    plt.title(f'Window with size: {w} and mean {m}')
    plt.imshow(ct_img, plt.cm.bone)


def get_dcm_uh(dir_path, num=3, save_folder=None):
    dcm_img_arrays = defaultdict(list)
    patient_ids = os.listdir(dir_path)
    for i, patient_id in enumerate(patient_ids[:num]):
        global nums_of_dcms

        if nums_of_dcms[i] < 40:
            try:
                patient_path = os.path.join(dir_path, patient_id)
                for j, dcm_img_name in enumerate(os.listdir(patient_path), start=1):
                    dcm_img_path = os.path.join(patient_path, dcm_img_name)
                    dcm_img = dicom.read_file(dcm_img_path)
                    dcm_img_array = dcm_img.pixel_array
                    if dcm_img_array.shape[0] != dcm_img_array.shape[1]:
                        dcm_img_array = crop_image(dcm_img_array)
                        dcm_img_array = dcm_img_array + 1024
                        dcm_img_array[dcm_img_array == np.min(dcm_img_array)] = 0
                        dcm_img_array = dcm_img_array - 1024
                    else:
                        dcm_img_array[dcm_img_array < 0] = 0

                    slope = int(dcm_img.RescaleSlope)
                    intercept = int(dcm_img.RescaleIntercept)
                    dcm_img_array = dcm_img_array * slope + intercept

                    # dcm_img_arrays[patient_id].append(dcm_img_array)

                    if save_folder:

                        if not os.path.isdir(save_folder):
                            os.mkdir(save_folder)
                        patient_folder = os.path.join(save_folder, patient_id)
                        if not os.path.isdir(patient_folder):
                            os.mkdir(patient_folder)
                        new_dcm_img_path = os.path.join(patient_folder, f'{j}.npy')

                        dcm_img_array = Image.fromarray(dcm_img_array)
                        size = (512, 512)
                        dcm_img_array = dcm_img_array.resize(size)
                        dcm_img_array = np.array(dcm_img_array)

                        np.save(new_dcm_img_path, dcm_img_array)

            except RuntimeError as err:
                print(f'Runtime error on patient {patient_id}:\n{err}')

        print(f'Patient {patient_id} - done. {num - i} patients left.')
    return dcm_img_arrays


dicom_train_path = 'data/raw/train'
absolute_dicom_train_path = os.path.join(project_dir, dicom_train_path)

# ==================================#
# Get number of dicom images of each patient
nums_of_dcms = []
for patient_dir in os.listdir(absolute_dicom_train_path):
    num_of_dcms = len(os.listdir(os.path.join(absolute_dicom_train_path, patient_dir)))

    nums_of_dcms.append(num_of_dcms)
# ==================================#
# Get data in HUs + save
# save_folder_path = os.path.join(project_dir, 'data/processed/train')
# data = get_dcm_uh(absolute_dicom_train_path, num=200, save_folder=save_folder_path)
# ==================================#
# To plot HU distribution hist

# total_hu_data = np.array([])
#
#
# def get_hu_distribution(hu_data, hist_bins=200, hist_range=None, concat=False):
#     global total_hu_data
#     hu_data = np.array(hu_data).flatten()
#     total_hu_data = np.concatenate((total_hu_data, hu_data))
#     if concat:
#         pass
#     else:
#         plt.hist(total_hu_data, bins=hist_bins, range=hist_range)
#         plt.show()

# ==================================#
# Preprocessing the CSV and saving it
train_csv_path = os.path.join(project_dir, 'data/raw/train.csv')

csv_df = pd.read_csv(train_csv_path)
processed_patients = os.listdir(project_dir + '/data/processed/train')

filt = pd.Series([True if x in processed_patients else False for x in csv_df['Patient']])
processed_csv_df = csv_df[filt]


def processSmokingStatus(patients_df):
    patients_df = patients_df.copy()
    statuses = patients_df['SmokingStatus'].unique()
    patients_df[statuses] = 0

    patients_df.reset_index(inplace=True)
    # for patient_id, smoking_status in zip(patients_df['Patient'], patients_df['SmokingStatus']):
    #     patients_df.loc[patient_id, smoking_status] = 1
    for j, smoking_status in enumerate(patients_df['SmokingStatus']):
        patients_df.loc[j, smoking_status] = 1
    return patients_df


def processSex(patients_df):
    patients_df = patients_df.copy()
    fem_filt = patients_df['Sex'] == 'Female'
    mal_filt = patients_df['Sex'] == 'Male'
    patients_df.loc[fem_filt, 'Sex_n'] = 0
    patients_df.loc[mal_filt, 'Sex_n'] = 1
    return patients_df


processed_csv_df = processSmokingStatus(processed_csv_df)
processed_csv_df = processSex(processed_csv_df)
processed_csv_df.drop('index', axis=1, inplace=True)
# processed_csv_df.to_csv(project_dir + '/data/processed/train.csv', index=False)
# ==================================#
# Hist the number of records for a person in processed dataset
patient_ids = processed_csv_df['Patient'].unique()
records_n = []

for ID in patient_ids:
    records_n.append(len(processed_csv_df[processed_csv_df['Patient'] == ID]))

# plt.hist(records_n, bins=10)
# ==================================#
# Plot the FVC and weeks graphs
weeks_x = []
FVC_y = []
for ID in patient_ids:
    weeks_x.append(processed_csv_df.loc[processed_csv_df['Patient'] == ID, 'Weeks'])
    FVC_y.append(processed_csv_df.loc[processed_csv_df['Patient'] == ID, 'FVC'])

# plt.figure(figsize=[14,14])
#
# for i, j in zip(weeks_x, FVC_y):
#     plt.plot(i, j)
#
# plt.show()
# ==================================#
# To plot hists of Age and number of dicom images of each patient
# plt.figure()
# plt.hist(csv_df.Age, bins=5)
# plt.show()
#
# plt.figure()
# plt.hist(nums_of_dcms, bins=30, range=[0, 1000])
# plt.show()
# ==================================#