# -*- coding: utf-8 -*-
"""
Last updated on Feb 12 2026

@author: bhejazi

GUI for surface smoothing

Surface smoothing takes the initial mesh points and categorizes them into even and 
odd. Mesh is smoothed by only keeping even points so that the number of points are reduced.
Reduced points are remeshed for a smoother surface using Poisson reconstruction.

.stl input is the initial .stl file and .stl output is final smoothed .stl file
mesh resolution determines the depth of the Poisson reconstruction. Must be >=2.
Default depth is set at 7, larger values mean higher resolution in the reconstruction.
"""

import sys
import os
import numpy as np

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QProgressBar, QComboBox, QSpinBox, QLineEdit, QMessageBox
)

# ---- import your smoothing function ----
from mesh_smoothing_function import mesh_smoothing, read_stl_unique, compute_vertex_normals_from_facets

# --- PyVista embedded viewer ---
from pyvistaqt import QtInteractor
import pyvista as pv

# ==========================================================
# Worker Thread (runs smoothing without freezing GUI)
# ==========================================================
class SmoothingWorker(QThread):
    progress = pyqtSignal(int)
    update_preview = pyqtSignal(str)     # emits file path for preview update
    finished = pyqtSignal(str)
    aborted = pyqtSignal()

    def __init__(self, params):
        super().__init__()
        self.params = params
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        iterations = self.params["iterations"]
        file_path = self.params["file_path"]
        save_path = self.params["save_path"]
        base_name = self.params["save_file_name"]
        depth = self.params["poisson_depth"]
        keep = self.params["keep"]

        try:
            for i in range(iterations):
                if not self._running:
                    self.aborted.emit()
                    return

                out_name = f"{base_name}_iter{i+1}"

                out_path = mesh_smoothing(
                    file_path=file_path,
                    poisson_depth=depth,
                    save_path=save_path,
                    save_file_name=out_name,
                    keep=keep,
                    seed=0,
                    visualize=False
                )

                # emit preview update
                self.update_preview.emit(out_path)

                # update progress
                pct = int((i + 1) / iterations * 100)
                self.progress.emit(pct)

                # next iteration uses previous output
                file_path = out_path

            # Done
            self.finished.emit(file_path)

        except Exception as e:
            self.finished.emit(f"ERROR: {str(e)}")

# ==========================================================
# Main GUI
# ==========================================================
class MeshSmoothingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mesh Smoothing GUI")
        self.setMinimumWidth(1200)
        self.setMinimumHeight(720)

        # FULL layout
        layout = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        # ---------------------
        # Embedded PyVista View
        # ---------------------
        self.plotter = QtInteractor(self)
        self.plotter.set_background("white")
        right.addWidget(self.plotter.interactor)

        # normals toggle
        self.toggle_normals_btn = QPushButton("Toggle Normals")
        self.toggle_normals_btn.clicked.connect(self.toggle_normals)
        right.addWidget(self.toggle_normals_btn)
        self.normals_visible = False

        # ---------------------
        # Controls on left side
        # ---------------------
        self.in_label = QLabel("Input STL File:")
        self.in_path = QLineEdit()
        self.btn_browse_in = QPushButton("Browse…")
        self.btn_browse_in.clicked.connect(self.pick_input_file)

        hl = QHBoxLayout()
        hl.addWidget(self.in_path)
        hl.addWidget(self.btn_browse_in)

        self.out_label = QLabel("Output Folder:")
        self.out_path = QLineEdit()
        self.btn_browse_out = QPushButton("Browse…")
        self.btn_browse_out.clicked.connect(self.pick_output_folder)

        hl2 = QHBoxLayout()
        hl2.addWidget(self.out_path)
        hl2.addWidget(self.btn_browse_out)

        # parameters
        self.name_label = QLabel("Output Base Name:")
        self.name_edit = QLineEdit("smoothed_mesh")

        self.depth_label = QLabel("Poisson Depth:")
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 15)
        self.depth_spin.setValue(7)

        self.keep_label = QLabel("Keep Vertices:")
        self.keep_combo = QComboBox()
        self.keep_combo.addItems(["even", "odd"])

        self.iter_label = QLabel("Iterations:")
        self.iter_spin = QSpinBox()
        self.iter_spin.setRange(1, 50)
        self.iter_spin.setValue(3)

        # progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)

        # run/cancel buttons
        self.btn_run = QPushButton("Run Smoothing")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_run.clicked.connect(self.run_smoothing)
        self.btn_cancel.clicked.connect(self.cancel_smoothing)

        # pack left side
        left.addWidget(self.in_label)
        left.addLayout(hl)
        left.addWidget(self.out_label)
        left.addLayout(hl2)
        left.addWidget(self.name_label)
        left.addWidget(self.name_edit)
        left.addWidget(self.depth_label)
        left.addWidget(self.depth_spin)
        left.addWidget(self.keep_label)
        left.addWidget(self.keep_combo)
        left.addWidget(self.iter_label)
        left.addWidget(self.iter_spin)
        left.addWidget(QLabel("Progress:"))
        left.addWidget(self.progress)
        left.addWidget(self.btn_run)
        left.addWidget(self.btn_cancel)
        left.addStretch()

        # Combine layout
        layout.addLayout(left, 1)
        layout.addLayout(right, 3)
        self.setLayout(layout)

        self.worker = None

    # =============== GUI EVENTS ====================
    def pick_input_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select STL File", "", "STL Files (*.stl)")
        if f:
            self.in_path.setText(f)
            self.load_mesh_preview(f)

    def pick_output_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if f:
            self.out_path.setText(f)

    def toggle_normals(self):
        self.normals_visible = not self.normals_visible
        self.update_normals_visibility()
 
    # =============== MESH RENDERING ====================
    def setup_lighting(self):
        """Configure PyVista/VTK renderer with high-quality lighting and shadows."""

        renderer = self.plotter.renderer

        # Clear default lights
        renderer.RemoveAllLights()

        # === Key Light (main directional light) ===
        key_light = pv.Light()
        key_light.set_direction_angle(45, -30)  # azimuth, elevation
        key_light.intensity = 0.9
        key_light.positional = False
        key_light.specular = 0.8
        key_light.diffuse = 1.0
        key_light.ambient = 0.2
        renderer.add_light(key_light)

        # === Fill Light (softens shadows) ===
        fill_light = pv.Light()
        fill_light.set_direction_angle(-60, 20)
        fill_light.intensity = 0.6
        fill_light.positional = False
        fill_light.specular = 0.3
        fill_light.diffuse = 0.7
        fill_light.ambient = 0.4
        renderer.add_light(fill_light)

        # === Back Light (rim lighting for silhouette edges) ===
        back_light = pv.Light()
        back_light.set_direction_angle(180, -20)
        back_light.intensity = 0.4
        back_light.positional = False
        back_light.specular = 0.4
        back_light.diffuse = 0.5
        renderer.add_light(back_light)

        # === Ambient light (uniform global light) ===
        ambient_light = pv.Light(light_type='ambient')
        ambient_light.intensity = 0.35
        renderer.add_light(ambient_light)

        # === Enable shadows ===
        renderer.SetUseShadows(True)

        # Shadow resolution (higher = better but slower)
        renderer.SetShadowStrength(0.5)  # softer shadows
        renderer.SetShadowBias(0.3)      # avoid shadow acne

        # Update window
        self.plotter.render()

    # =============== MESH PREVIEW ====================

    def load_mesh_preview(self, file_path):
        self.plotter.clear()
    
        if not os.path.isfile(file_path):
            return
    
        try:
            mesh = pv.read(file_path)
            self.current_mesh = mesh
    
            self.actor = self.plotter.add_mesh(
                mesh,
                color="lightgray",
                smooth_shading=True,            #
                specular=0.3,                   # nicer highlights
                specular_power=20,              # glossy appearance
                metallic=0.1,                   # subtle metallic look
                roughness=0.4,                  # softer reflections
            )
    
            self.setup_lighting()               # <<< enable new lighting/shadows
            self.plotter.reset_camera()
    
            # normals (if toggled)
            if self.normals_visible:
                self.add_normals(mesh)
    
        except Exception as e:
            print("Preview error:", e)


    def update_normals_visibility(self):
        if not hasattr(self, "current_mesh"):
            return
        self.plotter.clear()
        self.actor = self.plotter.add_mesh(self.current_mesh, color="lightgray")

        if self.normals_visible:
            self.add_normals(self.current_mesh)

        self.plotter.reset_camera()


    def add_normals(self, mesh):
        if "Normals" in mesh.array_names:
            normals = mesh["Normals"]
        else:
            return
    
        scale = 0.02 * np.linalg.norm(mesh.points.max(axis=0) - mesh.points.min(axis=0))
    
        self.normals_actor = self.plotter.add_arrows(
            mesh.points,
            normals * scale,
            color="red",
            lighting=True,
            smooth_shading=True
        )


    # =============== RUN / CANCEL ====================
    def run_smoothing(self):
        file_path = self.in_path.text().strip()
        save_path = self.out_path.text().strip()

        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "Error", "Input STL file does not exist.")
            return
        if not os.path.isdir(save_path):
            QMessageBox.warning(self, "Error", "Output folder does not exist.")
            return

        params = {
            "file_path": file_path,
            "save_path": save_path,
            "save_file_name": self.name_edit.text(),
            "poisson_depth": self.depth_spin.value(),
            "keep": self.keep_combo.currentText(),
            "iterations": self.iter_spin.value(),
        }

        self.progress.setValue(0)
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        self.worker = SmoothingWorker(params)
        self.worker.progress.connect(self.update_progress)
        self.worker.update_preview.connect(self.load_mesh_preview)
        self.worker.finished.connect(self.finish_run)
        self.worker.aborted.connect(self.abort_run)
        self.worker.start()

    def cancel_smoothing(self):
        if self.worker:
            self.worker.stop()

    def update_progress(self, value):
        self.progress.setValue(value)

    def finish_run(self, msg):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        QMessageBox.information(self, "Done", f"Finished smoothing.\nLast output: {msg}")

    def abort_run(self):
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        QMessageBox.information(self, "Cancelled", "Smoothing was cancelled.")


# ==========================================================
# Start GUI
# ==========================================================
def main():
    app = QApplication(sys.argv)
    gui = MeshSmoothingGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
