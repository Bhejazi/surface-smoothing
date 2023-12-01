# -*- coding: utf-8 -*-
"""
Created on Wed Nov 29 16:11:46 2023

@author: bhejazi
"""
import numpy as np
from stl import mesh
import open3d as o3d

def mesh_smoothing(file_path, poisson_depth, save_path, save_file_name):
    
    #%%          
    def read_stl(file_path):
        # Read the STL file
        mesh_data = mesh.Mesh.from_file(file_path)

        # Get the 3D vertex coordinates
        vertices = mesh_data.vectors.reshape((-1, 3))

        # Create a dictionary to map unique vertex coordinates to their indices
        vertex_dict = {}
        unique_vertices = []
        vertex_labels = []

        for vertex in vertices:
            vertex_tuple = tuple(vertex)
            if vertex_tuple not in vertex_dict:
                vertex_dict[vertex_tuple] = len(unique_vertices)
                unique_vertices.append(vertex)
                vertex_labels.append(vertex_dict[vertex_tuple])

        unique_vertices = np.array(unique_vertices)

        # Get the connectivity list (faces as indices of the vertex points)
        connectivity = []
        num_vertices_per_face = 3  # Assuming the STL file contains only triangular faces

        for i in range(0, len(vertices), num_vertices_per_face):
            face = [vertex_dict[tuple(vertices[j])] for j in range(i, i + num_vertices_per_face)]
            connectivity.append(face)

        return unique_vertices, np.array(connectivity)
    
    #%%
    pnts, connections = read_stl(file_path)
    pnts_list = np.arange(0, pnts.shape[0])
    odd_pnts = np.array([])
    even_pnts = np.array([])
    #%%
    print("Initial # of points: " + str(len(pnts_list)))
    
    counter = 0
    
    while len(pnts_list) > 0:
    
        counter += 1
        if np.mod(counter, 1000) == 0:
            print("# of points left to categorize: " + str(len(pnts_list)))
            
        rnd_pnt = np.random.choice(pnts_list)
        row, col = np.where(connections == rnd_pnt)
        connection_list = np.unique(connections[row, :])
              
        if connection_list.shape[0] == 1:
            connection_list = connection_list.reshape(-1, 1)
        
        for j in range(connection_list.shape[0]):
            if connection_list[j] == rnd_pnt:
                odd_pnts = np.append(odd_pnts, rnd_pnt)
            else:
                even_pnts = np.append(even_pnts, connection_list[j])
        
            pnts_list = np.setdiff1d(pnts_list, np.union1d(odd_pnts, even_pnts))
                
    even_pnts = np.unique(even_pnts)
        
    pnts_reduced = pnts[even_pnts.astype(int), :]
    #pnts_deleted = pnts[odd_pnts.astype(int), :]
            
    #%%
    # fig = plt.figure(3)
    # ax = fig.add_subplot(111, projection='3d')
    # ax.scatter(pnts_reduced[:, 0], pnts_reduced[:, 1], pnts_reduced[:, 2], c='r', marker='.')
    # ax.scatter(pnts_deleted[:, 0], pnts_deleted[:, 1], pnts_deleted[:, 2], c='b', marker='.')
    # plt.show()
    
    #%%
    point_cloud = pnts_reduced
    
    pcd  = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(point_cloud[:,:3])
    
    # visualize the point cloud
    # o3d.visualization.draw_geometries([pcd],window_name="Point Cloud", width=800, height=800)
    
    #%% Estimate point normals needed for meshing
    pcd.normals = o3d.utility.Vector3dVector(np.zeros((1, 3)))  # invalidate existing normals

    pcd.estimate_normals()
    #o3d.visualization.draw_geometries([pcd], point_show_normal=True)

    pcd.orient_normals_consistent_tangent_plane(100)

    print("See if normals are calculated correctly and pointing outward, close figures to continue.", flush=True)
    
    #%%
    o3d.visualization.draw_geometries([pcd], point_show_normal=True, width=800, height=800, 
                                      window_name="Normals")
    
    user_input = input("Are normals pointing outward? (y/n): ")

    # Check the user's response and execute the corresponding command
    if user_input.lower() == "y":
        print("Continuing to meshing.")
    elif user_input.lower() == "n":
        temp = np.array(pcd.normals)
        temp = -temp
        pcd.normals=o3d.utility.Vector3dVector(temp)
        o3d.visualization.draw_geometries([pcd], point_show_normal=True, width=800, height=800, 
                                      window_name="Normals after correction")
        print("Continuing to meshing.")
    else:
        print("Invalid input. Please enter 'y' or 'n'.")
    
    #%% Poisson reconstruction, has to have normals
    ## good for water tight meshes
    poisson_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=poisson_depth, width=0, 
                                                                             scale=1.1, linear_fit=False)
    
    poisson_mesh = poisson_mesh[0]
    poisson_mesh.compute_vertex_normals()
    poisson_mesh.paint_uniform_color([1, 0.706, 0])
    #o3d.visualization.draw_geometries([poisson_mesh], window_name="Mesh Poisson")
    
    with o3d.utility.VerbosityContextManager(
            o3d.utility.VerbosityLevel.Debug) as cm:
        triangle_clusters, cluster_n_triangles, cluster_area = (
            poisson_mesh.cluster_connected_triangles())
    triangle_clusters = np.asarray(triangle_clusters)
    cluster_n_triangles = np.asarray(cluster_n_triangles)
    cluster_area = np.asarray(cluster_area)
    
    largest_cluster_idx = cluster_n_triangles.argmax()
    triangles_to_remove = triangle_clusters != largest_cluster_idx
    poisson_mesh.remove_triangles_by_mask(triangles_to_remove)
    
    poisson_mesh.remove_degenerate_triangles()
    poisson_mesh.remove_duplicated_triangles()
    poisson_mesh.remove_duplicated_vertices()
    poisson_mesh.remove_non_manifold_edges()
    # assert poisson_mesh.is_watertight(), "Mesh has holes"
    
    # poisson_mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(poisson_mesh) # to tensor
    # filled_poisson_mesh = poisson_mesh_t.fill_holes()
    # assert filled_poisson_mesh.to_legacy().is_watertight(), "Mesh still has holes"
    
    # filled_poisson_mesh_final = filled_poisson_mesh.to_legacy()
    
    # print(filled_poisson_mesh_final)
    # o3d.visualization.draw_geometries([filled_poisson_mesh_final], window_name="Mesh Poisson removed small triangles", 
    #                                   width=800, height=800)
    print(poisson_mesh)
    o3d.visualization.draw_geometries([poisson_mesh], window_name="Mesh with Poisson method", 
                                      width=800, height=800)
    
    #%% Export mesh
    o3d.io.write_triangle_mesh(f"{save_path}\\{save_file_name}.stl", poisson_mesh)