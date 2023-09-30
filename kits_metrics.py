import os.path
from time import time
from typing import List, Tuple, Union

import numpy as np
import SimpleITK as sitk
from segmentationmetrics.surface_distance import (  # type: ignore
    compute_surface_dice_at_tolerance,
    compute_surface_distances,
)

####################################################################################################################################
# from https://github.com/neheller/kits23/blob/main/kits23/evaluation/dice.py


def dice(prediction: np.ndarray, reference: np.ndarray):
    """
    Both predicion and reference have to be bool (!) numpy arrays. True is interpreted as foreground, False is background
    """
    intersection = np.count_nonzero(prediction & reference)
    numel_pred = np.count_nonzero(prediction)
    numel_ref = np.count_nonzero(reference)
    if numel_ref == 0 and numel_pred == 0:
        return np.nan
    else:
        return 2 * intersection / (numel_ref + numel_pred)


####################################################################################################################################
# from https://github.com/neheller/kits23/blob/main/kits23/configuration/labels.py

# This is how we construct the hec regions from the labels. (1, 5, 6) means
# that labels 1, 5 and 6 will be merged and evaluated jointly in the
# corresponding hec region
KITS_HEC_LABEL_MAPPING = {
    "kidney_and_mass": (1, 2, 3),
    "mass": (2, 3),
    "tumor": (2,),
}

KITS_LABEL_TO_HEC_MAPPING = {j: i for i, j in KITS_HEC_LABEL_MAPPING.items()}

HEC_NAME_LIST = list(KITS_HEC_LABEL_MAPPING.keys())

# just for you as a reference. This tells you which metric is at what index.
# This is not used anywhere
METRIC_NAME_LIST = ["Dice", "SD"]

LABEL_AGGREGATION_ORDER = (1, 3, 2)
# this means that we first place the kidney, then the cyst and finally the
# tumor. The order matters! If parts of a later label (example tumor) overlap
# with a prior label (kidney or cyst) the prior label is overwritten

KITS_LABEL_NAMES = {1: "kidney", 2: "tumor", 3: "cyst"}

# values are determined by kits21/evaluation/compute_tolerances.py
HEC_SD_TOLERANCES_MM = {
    "kidney_and_mass": 1.0330772532390826,
    "mass": 1.1328796488598762,
    "tumor": 1.1498198361434828,
}

####################################################################################################################################
# from https://github.com/neheller/kits23/blob/main/kits23/evaluation/generate_bool_masks_for_hec.py


def construct_HEC_from_segmentation(
    segmentation: np.ndarray, label: Union[int, Tuple[int, ...]]
) -> np.ndarray:
    """
    Takes a segmentation as input (integer map with values indicating what class a voxel belongs to) and returns a
    boolean array based on where the selected label/HEC is. If label is a tuple, all pixels belonging to any of the
    listed classes will be set to True in the results. The rest remains False.
    """
    if not isinstance(label, (tuple, list)):
        return segmentation == label
    else:
        if len(label) == 1:
            return segmentation == label[0]
        else:
            mask = np.zeros(segmentation.shape, dtype=bool)
            for l in label:
                mask[segmentation == l] = True
            return mask


####################################################################################################################################
# from https://github.com/neheller/kits23/blob/main/kits23/evaluation/metrics.py


def compute_metrics_for_label(
    segmentation_predicted: np.ndarray,
    segmentation_reference: np.ndarray,
    label: Union[int, Tuple[int, ...]],
    spacing: Tuple[float, ...],
    sd_tolerance_mm: float = None,
) -> Tuple[float, float]:
    """
    :param segmentation_predicted: segmentation map (np.ndarray) with int values representing the predicted segmentation
    :param segmentation_reference:  segmentation map (np.ndarray) with int values representing the gt segmentation
    :param label: can be int or tuple of ints. If tuple of ints, a HEC is constructed from the labels in the tuple.
    :param spacing: important to know for volume and surface distance computation
    :param sd_tolerance_mm
    :return:
    """
    assert all(
        [i == j]
        for i, j in zip(segmentation_predicted.shape, segmentation_reference.shape)
    ), "predicted and gt segmentation must have the same shape"

    # make label always a tuple. Needed for inferring sd_tolerance_mm if not given
    label = (label,) if not isinstance(label, (tuple, list)) else label

    # build a bool mask from the segmentation_predicted, segmentation_reference and provided label(s)
    mask_pred = construct_HEC_from_segmentation(segmentation_predicted, label)
    mask_gt = construct_HEC_from_segmentation(segmentation_reference, label)
    gt_empty = np.count_nonzero(mask_gt) == 0
    pred_empty = np.count_nonzero(mask_pred) == 0

    if sd_tolerance_mm is None:
        sd_tolerance_mm = HEC_SD_TOLERANCES_MM[KITS_LABEL_TO_HEC_MAPPING[label]]

    if gt_empty and pred_empty:
        sd = 1
        dc = 1
    elif gt_empty or pred_empty:
        sd = 0
        dc = 0
    else:
        dc = dice(mask_pred, mask_gt)
        dist = compute_surface_distances(mask_gt, mask_pred, spacing)
        sd = compute_surface_dice_at_tolerance(dist, tolerance_mm=sd_tolerance_mm)

    return dc, sd


def compute_metrics_for_case(
    fname_pred: Union[str, sitk.Image], fname_ref: Union[str, sitk.Image]
) -> np.ndarray:
    """
    Takes two .nii.gz segmentation maps and computes the KiTS metrics for all HECs. The return value of this function
    is an array of size num_HECs x num_metrics.
    The order of metrics in the tuple follows the order on the KiTS website (https://kits23.kits-challenge.org/):
    -> Dice (1 is best)
    -> Surface Dice (1 is best)
    :param fname_pred: filename of the predicted segmentation
    :param fname_ref: filename of the ground truth segmentation
    :return: np.ndarray of shape 3x2 (labels x metrics). Labels are HECs in the order given by HEC_NAME_LIST
    """
    if isinstance(fname_pred, sitk.Image):
        img_pred = fname_pred
    else:
        img_pred = sitk.ReadImage(fname_pred)
    if isinstance(fname_ref, sitk.Image):
        img_ref = fname_ref
    else:
        img_ref = sitk.ReadImage(fname_ref)

    # we need to invert the spacing because SimpleITK is weird
    spacing_pred = list(img_pred.GetSpacing())[::-1]
    spacing_ref = list(img_ref.GetSpacing())[::-1]

    if not all([i == j] for i, j in zip(spacing_pred, spacing_ref)):
        # no need to make this an error. We can evaluate successfullt as long as the shapes match.
        print(
            "WARNING: predicted and reference segmentation do not have the same spacing!"
        )

    img_pred_npy = sitk.GetArrayFromImage(img_pred)
    img_gt_npy = sitk.GetArrayFromImage(img_ref)

    metrics = np.zeros((len(HEC_NAME_LIST), 2), dtype=float)
    for i, hec in enumerate(HEC_NAME_LIST):
        metrics[i] = compute_metrics_for_label(
            img_pred_npy,
            img_gt_npy,
            KITS_HEC_LABEL_MAPPING[hec],
            tuple(spacing_pred),
            sd_tolerance_mm=HEC_SD_TOLERANCES_MM[hec],
        )
    return metrics
