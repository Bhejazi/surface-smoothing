# Surface smoothing
This program takes as input a `.stl` file of a rough surface mesh and returns a smoothed surface mesh.

## Installation
Clone the repository (or download it's contents manually):
```shell
git clone https://github.com/Bhejazi/surface_smoothing.git
```
Recommended to use Python 3.7 with the libraries in requirments.txt

Navigate to the downloaded folder location and install dependencies:
```shell
python -m pip install -r requirements.txt
```

## Usage
The program is usable with a graphical user interface (GUI) in combination with a command line interface for calculation steps.

To run the program enter:
```shell
python gui_mesh_smoothing.py
```

## Notes
| Term | Explanation |
|------|-------------|
| Data type | Choose input data type. Can be either a mesh with .stl format or a point cloud in .npy format |
| Input data path | Browse and select the input data file |
| Meshing resolution  | Sets the depth of the octree used for the Poisson surface reconstruction. Must be a value greater than 2. Options are for values between 2 and 10 where larger numbers represent increased resolution. Suggested to start with 7 and adjust accordingly. |
| .stl output path | Directory to save the smoothed outout .stl file |
| Save file name | Smoothed outout .stl file name |

Note: If the input data is a mesh, in addition to saving an output smoothed mesh, a point cloud of the reduced mesh vertices used for creating a smooth mesh is also saved. This is so that if you need to run the surface reconstruction again with a different _Mesh resolution_, you can directly use the already calculated reduced points and not have to rerun that section agian.

## Sources
[1]: Qian-Yi Zhou, Jaesik Park, Vladlen Koltun, _Open3D: A Modern Library for 3D Data Processing_, arXiv:1801.09847, 2018

http://www.open3d.org/

[2]: Hussein S. Abdul-Rahman, Xiangqian Jane Jiang, Paul J. Scott, _Freeform surface filtering using the lifting wavelet transform_, Precision Engineering, Volume 37, Issue 1, Pages 187-202, 2013

https://doi.org/10.1016/j.precisioneng.2012.08.002
