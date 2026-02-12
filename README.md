# Surface smoothing
This program takes as input a `.stl` file of a rough surface mesh and returns a smoothed surface mesh.

## Installation
Clone the repository (or download it's contents manually):
```shell
git clone https://github.com/Bhejazi/surface_smoothing.git
```
📁 Navigate to the code working directory.

Create your new environemnt with Conda:
```shell
conda create -n mesh-smth --file conda-requirements.txt -c conda-forge
```

Activate the the Conda environemnt:
```shell
conda activate mesh-smth
```

## Usage
The program runs using a graphical user interface (GUI).

To run the program enter:
```shell
python mesh_smoothing_gui.py
```

## GUI operation
| Term | Explanation |
|------|-------------|
| Input `.stl` File | Browse and select the input `.stl` file |
| Output Folder | Output path for each iteration’s output |
| Output File Name | Output file name base |
| Meshing resolution (Poisson depth)  | Sets the depth of the octree used for the Poisson surface reconstruction. Default is 7 and adjust accordingly. |
| Keep Vertices | Choose even or odd |
| Number of Smoothing Iterations | How many times to run the smoothing (each iteration uses the previous output) |

➡️ Click Run Smoothing to begin

Progress bar shows percentage of completion,
Use Cancel to abort.

Outputs will be saved as:
```shell
<output_folder>/<base_name>_iter1.stl
<output_folder>/<base_name>_iter2.stl
```

## Sources
[1]: Qian-Yi Zhou, Jaesik Park, Vladlen Koltun, _Open3D: A Modern Library for 3D Data Processing_, arXiv:1801.09847, 2018

http://www.open3d.org/

[2]: Hussein S. Abdul-Rahman, Xiangqian Jane Jiang, Paul J. Scott, _Freeform surface filtering using the lifting wavelet transform_, Precision Engineering, Volume 37, Issue 1, Pages 187-202, 2013

https://doi.org/10.1016/j.precisioneng.2012.08.002
