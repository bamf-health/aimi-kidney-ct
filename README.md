# Kidney CT Segmentation

The kidney tumor segmentation model is trained on contrast CT (corticomedullary and nephrogenic phases) to accurately delineate the kidney, tumor, and cysts. The [KiTS 2023](https://kits-challenge.org/kits23/) dataset is employed to train a kidney tumor segmentation model (N=489) using an ensemble of fivefold cross-validation within the [nnUNet](https://github.com/MIC-DKFZ/nnUNet/tree/master/documentation) framework. In the first stage, the trained model generated annotations for 64 cases from [TCGA-KIRC](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=5800386) collection. These annotations were refined by non-experts. Among these, 45 cases added to the [KiTS 2023](https://kits-challenge.org/kits23/) dataset as the training set for the second stage model. The final model is used to generate annotations for 156 cases from [TCGA-KIRC](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=5800386) collection which includes 43 cases from first stage (27 train and 16 test TCGA-KIRC cases). Additionally, radiologists annotated the remaining 39 out of the 156 cases, enabling a comparison between the final model's segmentation and radiologist annotations.[TCGA-KIRC](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=5800386) collection.

The [model_performance](model_performance.ipynb) notebook contains the code to evaluate the model performance on the [TCGA-KIRC](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=5800386) collection against a validation evaluated by a radiologist and a non-expert.

## Running the model

#TODO

### Build container from pretrained weights

#TODO

### Running inference

By default the container takes an input directory that contains DICOM files of CT scans, and an output directory where DICOM-SEG files will be placed. To run on multiple scans, place DICOM files for each scan in a separate folder within the input directory. The output directory will have a folder for each input scan, with the DICOM-SEG file inside.

example:

#TODO

There is an optional `--nifti` flag that will take nifti files as input and output.

#### Run inference on IDC Collections

This model was run on CT scans from the [TCGA-KIRC](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=5800386) collection. The AI segmentations and corrections by a radioloist for 10% of the dataset are available in the kidney-ct.zip file on the [zenodo record](https://zenodo.org/record/8352041)

You can reproduce the results with the [run_on_idc_data](run_on_idc_data.ipynb) notebook on google colab.

### Training your own weights

Refer to the [training instructions](training.md) for more details. #TODO
