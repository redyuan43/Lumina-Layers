import os
import sys

import numpy as np


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def test_single_sided_voxel_matrix_keeps_face_down_but_reverses_optical_stack():
    from core.converter import _build_voxel_matrix

    material_matrix = np.array([[[0, 1, 2, 3, 4]]], dtype=int)
    mask_solid = np.array([[True]])

    full_matrix, metadata = _build_voxel_matrix(
        material_matrix=material_matrix,
        mask_solid=mask_solid,
        spacer_thick=0.16,
        structure_mode="Single-sided",
        backing_color_id=9,
    )

    assert metadata["backing_z_range"] == (5, 6)
    assert full_matrix[:, 0, 0].tolist() == [4, 3, 2, 1, 0, 9, 9]


def test_double_sided_voxel_matrix_keeps_bottom_face_down_and_top_mirrored():
    from core.converter import _build_voxel_matrix

    material_matrix = np.array([[[0, 1, 2, 3, 4]]], dtype=int)
    mask_solid = np.array([[True]])

    full_matrix, metadata = _build_voxel_matrix(
        material_matrix=material_matrix,
        mask_solid=mask_solid,
        spacer_thick=0.16,
        structure_mode="Double-sided",
        backing_color_id=9,
    )

    assert metadata["backing_z_range"] == (5, 6)
    assert full_matrix[:, 0, 0].tolist() == [0, 1, 2, 3, 4, 9, 9, 4, 3, 2, 1, 0]
