"""Unit tests for the vector branch export in converter.py.

Validates that:
    1. The vector branch calls export_scene_with_bambu_metadata (not scene.export).
    2. The slot_names passed to the exporter match the scene's geometry keys.
"""

import sys
import os
import types
import json
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

# Add project root to path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Stub heavy third-party modules that core.__init__ transitively imports
# so we can test the converter without installing them in CI.
# Use a smarter stub that preserves gr.update() behavior.
for _mod_name in ("gradio", "gradio.themes"):
    if _mod_name not in sys.modules:
        _mock = MagicMock()
        # Preserve gr.update() returning a real dict so downstream tests work
        if _mod_name == "gradio":
            _mock.update = lambda **kwargs: {"__type__": "update", **kwargs}
        sys.modules[_mod_name] = _mock

import pytest
import trimesh
import numpy as np
from utils.bambu_3mf_writer import export_scene_with_bambu_metadata, BambuStudio3MFWriter


def _build_fake_processor(scene):
    """Return a MagicMock that behaves like VectorProcessor."""
    vp = MagicMock()
    vp.svg_to_mesh.return_value = scene
    vp.img_processor.lut_rgb = np.zeros((256, 3))
    vp.img_processor._load_svg.return_value = np.zeros((100, 100, 4), dtype=np.uint8)
    return vp


# =====================================================================
# 1. Vector branch uses Bambu metadata export
# =====================================================================

class TestVectorBranchExport:
    """Confirm the vector conversion path goes through the unified
    Bambu metadata exporter rather than the plain trimesh export."""

    @patch("core.converter.export_scene_with_bambu_metadata")
    @patch("core.vector_engine.VectorProcessor")
    def test_bambu_export_called(self, MockVP, mock_bambu_export, tmp_path):
        """export_scene_with_bambu_metadata should be invoked for SVG vector mode."""
        from config import ModelingMode

        svg_file = tmp_path / "test.svg"
        svg_file.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
            '<rect x="0" y="0" width="100" height="100" fill="#ff0000"/>'
            '</svg>'
        )

        fake_scene = trimesh.Scene()
        mesh = trimesh.creation.box(extents=[10, 10, 1])
        mesh.metadata["name"] = "White"
        mesh.visual.face_colors = [255, 255, 255, 255]
        fake_scene.add_geometry(mesh, geom_name="White")

        MockVP.return_value = _build_fake_processor(fake_scene)

        from core.converter import convert_image_to_3d

        dummy_lut = str(tmp_path / "dummy.npy")
        np.save(dummy_lut, np.zeros(10))

        convert_image_to_3d(
            image_path=str(svg_file),
            lut_path=dummy_lut,
            target_width_mm=50.0,
            spacer_thick=1.6,
            structure_mode="Single-sided",
            auto_bg=False,
            bg_tol=30,
            color_mode="4-Color",
            add_loop=False,
            loop_width=5, loop_length=20, loop_hole=3, loop_pos="Top",
            modeling_mode=ModelingMode.VECTOR,
        )

        mock_bambu_export.assert_called_once()

    @patch("core.converter.export_scene_with_bambu_metadata")
    @patch("core.vector_engine.VectorProcessor")
    def test_slot_names_match_scene_geometry(self, MockVP, mock_bambu_export, tmp_path):
        """slot_names passed to exporter should equal list(scene.geometry.keys())."""
        from config import ModelingMode

        svg_file = tmp_path / "test2.svg"
        svg_file.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50">'
            '<circle cx="25" cy="25" r="20" fill="#0000ff"/>'
            '</svg>'
        )

        fake_scene = trimesh.Scene()
        for name in ["White", "Cyan", "Board"]:
            m = trimesh.creation.box(extents=[5, 5, 0.5])
            m.metadata["name"] = name
            fake_scene.add_geometry(m, geom_name=name)

        MockVP.return_value = _build_fake_processor(fake_scene)

        from core.converter import convert_image_to_3d

        dummy_lut = str(tmp_path / "dummy2.npy")
        np.save(dummy_lut, np.zeros(10))

        convert_image_to_3d(
            image_path=str(svg_file),
            lut_path=dummy_lut,
            target_width_mm=30.0,
            spacer_thick=1.6,
            structure_mode="Single-sided",
            auto_bg=False,
            bg_tol=30,
            color_mode="4-Color",
            add_loop=False,
            loop_width=5, loop_length=20, loop_hole=3, loop_pos="Top",
            modeling_mode=ModelingMode.VECTOR,
        )

        _, kwargs = mock_bambu_export.call_args
        assert kwargs["slot_names"] == ["White", "Cyan", "Board"]

    @patch("core.converter.export_scene_with_bambu_metadata")
    @patch("core.vector_engine.VectorProcessor")
    def test_empty_scene_returns_error(self, MockVP, mock_bambu_export, tmp_path):
        """Empty vector scene should fail before exporter is called."""
        from config import ModelingMode

        svg_file = tmp_path / "empty.svg"
        svg_file.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            '<rect x="0" y="0" width="10" height="10" fill="#ffffff"/>'
            '</svg>'
        )

        empty_scene = trimesh.Scene()
        MockVP.return_value = _build_fake_processor(empty_scene)

        from core.converter import convert_image_to_3d

        dummy_lut = str(tmp_path / "dummy3.npy")
        np.save(dummy_lut, np.zeros(10))

        out_path, glb_path, preview_img, msg, _ = convert_image_to_3d(
            image_path=str(svg_file),
            lut_path=dummy_lut,
            target_width_mm=20.0,
            spacer_thick=1.6,
            structure_mode="Single-sided",
            auto_bg=False,
            bg_tol=30,
            color_mode="4-Color",
            add_loop=False,
            loop_width=5, loop_length=20, loop_hole=3, loop_pos="Top",
            modeling_mode=ModelingMode.VECTOR,
        )

        assert out_path is None
        assert glb_path is None
        assert preview_img is None
        assert "no valid geometry" in msg.lower()
        mock_bambu_export.assert_not_called()


class TestBambuExportGuardrails:

    def test_export_scene_raises_on_missing_slot_geometry(self, tmp_path):
        scene = trimesh.Scene()
        scene.add_geometry(trimesh.creation.box(extents=[5, 5, 1]), geom_name="White")

        out_path = tmp_path / "out.3mf"
        with pytest.raises(ValueError, match="Missing geometries"):
            export_scene_with_bambu_metadata(
                scene=scene,
                output_path=str(out_path),
                slot_names=["White", "Cyan"],
                preview_colors={0: [255, 255, 255, 255], 1: [0, 134, 214, 255]},
                settings={},
                color_mode="4-Color",
            )

    def test_writer_add_mesh_rejects_empty_mesh(self, tmp_path):
        writer = BambuStudio3MFWriter(str(tmp_path / "x.3mf"), settings={}, color_mode="4-Color")
        empty = trimesh.Trimesh(vertices=np.zeros((0, 3)), faces=np.zeros((0, 3), dtype=np.int64))
        with pytest.raises(ValueError, match="empty geometry"):
            writer.add_mesh(empty, "White", (255, 255, 255))

    def test_backing_reuses_white_extruder_without_ninth_filament(self, tmp_path):
        scene = trimesh.Scene()
        slot_names = [
            "Slot 1 (White)",
            "Slot 2 (Cyan)",
            "Slot 3 (Magenta)",
            "Slot 4 (Yellow)",
            "Slot 5 (Black)",
            "Slot 6 (Red)",
            "Slot 7 (Deep Blue)",
            "Slot 8 (Green)",
            "Backing",
        ]
        preview_colors = {
            0: [255, 255, 255, 255],
            1: [0, 163, 222, 255],
            2: [219, 42, 162, 255],
            3: [244, 220, 69, 255],
            4: [0, 0, 0, 255],
            5: [241, 41, 25, 255],
            6: [0, 76, 201, 255],
            7: [172, 232, 153, 255],
        }
        for name in slot_names:
            scene.add_geometry(trimesh.creation.box(extents=[1, 1, 0.2]), geom_name=name)

        out_path = tmp_path / "eight_with_backing.3mf"
        export_scene_with_bambu_metadata(
            scene=scene,
            output_path=str(out_path),
            slot_names=slot_names,
            preview_colors=preview_colors,
            settings={},
            color_mode="8-Color Max",
        )

        with zipfile.ZipFile(out_path) as zf:
            model_settings = zf.read("Metadata/model_settings.config")
            project_settings = json.loads(zf.read("Metadata/project_settings.config"))

        root = ET.fromstring(model_settings)
        parts = root.findall("./object/part")
        extruders_by_name = {}
        for part in parts:
            metadata = {
                item.attrib["key"]: item.attrib["value"]
                for item in part.findall("metadata")
            }
            extruders_by_name[metadata["name"]] = metadata["extruder"]

        assert extruders_by_name["Backing"] == "1"
        assert "9" not in extruders_by_name.values()
        assert len(project_settings["filament_colour"]) == 8
        assert project_settings["filament_colour"][0] == "#FFFFFF"

    def test_svg_board_reuses_white_extruder(self, tmp_path):
        scene = trimesh.Scene()
        for name in ["White", "Cyan", "Board"]:
            scene.add_geometry(trimesh.creation.box(extents=[1, 1, 0.2]), geom_name=name)

        out_path = tmp_path / "board.3mf"
        export_scene_with_bambu_metadata(
            scene=scene,
            output_path=str(out_path),
            slot_names=["White", "Cyan", "Board"],
            preview_colors={0: [255, 255, 255, 255], 1: [0, 255, 255, 255]},
            settings={},
            color_mode="CMYW",
        )

        with zipfile.ZipFile(out_path) as zf:
            root = ET.fromstring(zf.read("Metadata/model_settings.config"))
            project_settings = json.loads(zf.read("Metadata/project_settings.config"))

        extruders_by_name = {}
        for part in root.findall("./object/part"):
            metadata = {
                item.attrib["key"]: item.attrib["value"]
                for item in part.findall("metadata")
            }
            extruders_by_name[metadata["name"]] = metadata["extruder"]

        assert extruders_by_name["Board"] == "1"
        assert len(project_settings["filament_colour"]) == 4
