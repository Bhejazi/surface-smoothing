# -*- coding: utf-8 -*-
"""
Created on Wed Nov 29 16:11:46 2023

@author: bhejazi
"""
import numpy as np
import open3d as o3d
#%%
def mesh_smoothing(data_type, file_path, poisson_depth, save_path, save_file_name):
    #%%          
    def read_stl(file_path):
        # Read the STL file
        mesh_data = o3d.io.read_triangle_mesh(file_path)
        # Get the 3D vertex coordinates
        vertices = np.asarray(mesh_data.vertices)
        vert_norms = np.asarray(mesh_data.vertex_normals)
        connectivity = np.asarray(mesh_data.triangles)
        
        return vertices, vert_norms, connectivity
    #%%
    if data_type == "Mesh":
        
        print("Reducing mesh points...")
        pnts, norms, connections = read_stl(file_path)
        
        pnts_list = np.arange(0, pnts.shape[0])
        odd_pnts = np.array([])
        even_pnts = np.array([])
        #%%
        print("Initial # of points: " + str(len(pnts_list)))
        
        counter = 0
        
        while len(pnts_list) > 0:
        
            counter += 1
            if np.mod(counter, 2000) == 0:
                print("# of points left to categorize: " + str(len(pnts_list)))
                
            rnd_pnt = np.random.choice(pnts_list)
            rnd_vert = pnts[rnd_pnt, :]
            rnd_vert_list = np.array(np.where((pnts[:,0] == rnd_vert[0]) & (pnts[:,1] == rnd_vert[1]) & (pnts[:,2] == rnd_vert[2])))
            connection_list = np.array([])
            
            odd_pnts = np.append(odd_pnts, rnd_vert_list)
            
            for i in range(rnd_vert_list.shape[1]):
                row, col = np.where(connections == rnd_vert_list[0,i])
                connection_list = np.append(connection_list, connections[row, :])
                
            connection_list = np.setdiff1d(connection_list, rnd_vert_list)
            connection_list = connection_list.astype(int)
            
            for j in range(connection_list.shape[0]):
                even_pnt = pnts[connection_list[j], :]
                even_pnt_list = np.array(np.where((pnts[:,0] == even_pnt[0]) & (pnts[:,1] == even_pnt[1]) & (pnts[:,2] == even_pnt[2])))
                even_pnts = np.append(even_pnts, even_pnt_list)

            pnts_list = np.setdiff1d(pnts_list, np.union1d(odd_pnts, even_pnts))
                    
        even_pnts = np.unique(even_pnts)
            
        pnts_reduced = pnts[even_pnts.astype(int), :]
        norms_reduced = norms[even_pnts.astype(int), :]
        np.save(f"{save_path}\\{save_file_name}.npy", pnts_reduced, norms_reduced)
        #pnts_deleted = pnts[odd_pnts.astype(int), :]
    elif data_type == "Point cloud":
        pnts_reduced = np.load(file_path)
        norms_reduced = np.load(file_path) 
    else:
        print("Invalid input data type.")           
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
    pcd.normals = o3d.utility.Vector3dVector(norms_reduced)    #o3d.visualization.draw_geometries([pcd], point_show_normal=True)
                
    # o3d.visualization.draw_geometries([pcd], point_show_normal=True, width=800, height=800, window_name="Normals")
    #%% Poisson reconstruction, has to have normals
    ## good for water tight meshes
    print("Meshing reduced points...")
    poisson_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=poisson_depth, width=0, scale=1.1, linear_fit=False)
        
    poisson_mesh = poisson_mesh[0]
    poisson_mesh.compute_vertex_normals()
    poisson_mesh.paint_uniform_color([1, 0.706, 0])
        
    #with o3d.utility.VerbosityContextManager(
    #        o3d.utility.VerbosityLevel.Debug) as cm:
    triangle_clusters, cluster_n_triangles, cluster_area = (poisson_mesh.cluster_connected_triangles())
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

    #%% Export mesh  
    o3d.io.write_triangle_mesh(f"{save_path}\\{save_file_name}.stl", poisson_mesh)
    # Visualize mesh
    o3d.visualization.draw_geometries([poisson_mesh], window_name="Mesh with Poisson method", width=800, height=800)