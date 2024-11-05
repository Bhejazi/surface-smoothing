# -*- coding: utf-8 -*-
"""
Created on Wed Nov 29 16:02:02 2023

@author: bhejazi

GUI for surface smoothing

Surface smoothing takes the initial mesh points and splits them into even and 
odd. Mesh is smoothed by only keeping even points so that the number of points are reduced.
Reduced points are remeshed for a smoother surface using Poisson reconstruction.

.stl input is the initial .stl file and .stl output is final smoothed .stl file
mesh resolution determines the depth of the Poisson reconstruction. Must be >=2.
Default depth is set at 7, larger values mean higher resolution in the reconstruction.

"""
#%% Import libraries
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from mesh_smoothing_function import mesh_smoothing

def run_code():
    data_type = data_type_entry.get()
    file_path = file_entry.get()
    poisson_depth = int(poisson_depth_entry.get())
    save_path = save_entry.get()  # Get the save path
    save_file_name = save_file_name_entry.get()  # Get the save file name

    mesh_smoothing(data_type, file_path, poisson_depth, save_path, save_file_name)
    
def browse_file():
    file_path = filedialog.askopenfilename()
    file_entry.delete(0, tk.END)
    file_entry.insert(0, file_path)
    
def browse_save_path():
    save_path = filedialog.askdirectory()
    save_entry.delete(0, tk.END)
    save_entry.insert(0, save_path)

# Create the main window
root = tk.Tk()
root.title("Surface Smoothing")

# Data Type Entry
data_type_label = ttk.Label(root, text="Data type:")
data_type_label.grid(row=0, rowspan=1, column=0, sticky=tk.W, padx=5, pady=5)
data_type_values = [i for i in ["Mesh", "Point cloud"]]  # data type either mesh or point cloud
data_type_entry = ttk.Combobox(root, values=data_type_values)
data_type_entry.grid(row=0, column=1, padx=5, pady=5)
data_type_entry.set(data_type_values[0])  # Set default value

# File Path Entry
file_label = ttk.Label(root, text="Input data path:")
file_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
file_entry = ttk.Entry(root, width=40)
file_entry.grid(row=1, column=1, padx=5, pady=5)
browse_button = ttk.Button(root, text="Browse", command=browse_file)
browse_button.grid(row=1, column=3, padx=5, pady=5)

# Poisson Depth Entry
poisson_depth_label = ttk.Label(root, text="Meshing resolution:")
#poisson_depth_label_next_line = ttk.Label(root, text="(>=2, default=8, larger values correspond to higher resolution)")
poisson_depth_label.grid(row=2, rowspan=1, column=0, sticky=tk.W, padx=5, pady=5)
#poisson_depth_label_next_line.grid(row=2, rowspan=1, column=0, sticky=tk.W, padx=5, pady=5)
#poisson_depth_entry = ttk.Entry(root)
#poisson_depth_entry.grid(row=1, column=1, padx=5, pady=5)
poisson_depth_values = [str(i) for i in range(2, 11)]  # poisson_depth values from 2 to 10
poisson_depth_entry = ttk.Combobox(root, values=poisson_depth_values)
poisson_depth_entry.grid(row=2, column=1, padx=5, pady=5)
poisson_depth_entry.set(poisson_depth_values[5])  # Set default value

# Save Path Entry
save_label = ttk.Label(root, text=".stl output path:")
save_label.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
save_entry = ttk.Entry(root, width=40)
save_entry.grid(row=3, column=1, padx=5, pady=5)
browse_save_button = ttk.Button(root, text="Browse", command=browse_save_path)
browse_save_button.grid(row=3, column=3, padx=5, pady=5)

# Save file name entry
save_file_name_label = ttk.Label(root, text="Save file name:")
save_file_name_label.grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
save_file_name_entry = ttk.Entry(root)
save_file_name_entry.grid(row=4, column=1, padx=5, pady=5)

# Run Button
run_button = ttk.Button(root, text="Run Code", command=run_code)
run_button.grid(row=5, column=0, columnspan=4, pady=10)

# Start the GUI event loop
root.mainloop()
