# -*- coding: utf-8 -*-
"""
Updated on Feb 12 2026

Mesh smoothing via vertex reduction (odd/even) while preserving correct outward normals
from STL facet normals, followed by Poisson surface reconstruction.

Created by Bardia Hejazi
"""

import os
import numpy as np
from stl import mesh as npstl_mesh
import open3d as o3d
from typing import Tuple, Optional

# ---------------------------
# Utilities
# ---------------------------

def _normalize_rows(v: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Row-wise normalization with safe divide."""
    n = np.linalg.norm(v, axis=1, keepdims=True)
    n = np.maximum(n, eps)
    return v / n

def read_stl_unique(file_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Read STL using numpy-stl and return:
      - unique vertices: (V, 3)
      - connectivity (triangles by vertex indices): (F, 3)
      - facet normals (from STL): (F, 3)
    """
    m = npstl_mesh.Mesh.from_file(file_path)  # triangles as (F, 3, 3)
    tris = m.vectors
    facet_normals = m.normals

    # Build unique vertex list and index mapping
    vertex_dict = {}
    unique_vertices = []
    connectivity = []

    def key(v):
        # STL typically uses exact float duplicates across shared vertices,
        # but we still key on tuple to deduplicate.
        return (v[0], v[1], v[2])

    for tri in tris:
        face_idx = []
        for v in tri:
            k = key(v)
            if k not in vertex_dict:
                vertex_dict[k] = len(unique_vertices)
                unique_vertices.append([v[0], v[1], v[2]])
            face_idx.append(vertex_dict[k])
        connectivity.append(face_idx)

    unique_vertices = np.asarray(unique_vertices, dtype=np.float64)
    connectivity = np.asarray(connectivity, dtype=np.int64)
    facet_normals = np.asarray(facet_normals, dtype=np.float64)

    # Normalize facet normals defensively
    facet_normals = _normalize_rows(facet_normals)

    return unique_vertices, connectivity, facet_normals

def compute_vertex_normals_from_facets(
    vertices: np.ndarray,
    faces: np.ndarray,
    facet_normals: np.ndarray,
    weight: str = "area",
) -> np.ndarray:
    """
    Compute per-vertex normals as a weighted sum of incident facet normals.

    Args:
        vertices: (V, 3)
        faces: (F, 3) integer indices into vertices
        facet_normals: (F, 3) outward-oriented facet normals from STL
        weight: 'area' | 'uniform'
    Returns:
        vertex_normals: (V, 3) outward vertex normals
    """
    V = vertices.shape[0]
    F = faces.shape[0]
    vnorms = np.zeros((V, 3), dtype=np.float64)

    if weight == "area":
        # Triangle area as weight
        v0 = vertices[faces[:, 0]]
        v1 = vertices[faces[:, 1]]
        v2 = vertices[faces[:, 2]]
        areas = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
        w = areas[:, None]  # (F, 1)
    else:
        w = np.ones((F, 1), dtype=np.float64)

    contrib = facet_normals * w  # (F, 3)

    for f in range(F):
        i, j, k = faces[f]
        vnorms[i] += contrib[f]
        vnorms[j] += contrib[f]
        vnorms[k] += contrib[f]

    return _normalize_rows(vnorms)

def greedy_even_odd_partition(
    faces: np.ndarray,
    n_vertices: int,
    seed: Optional[int] = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Partition vertices into 'odd' and 'even' similar to the original code:
      - Pick a random unassigned vertex -> assign to odd
      - Assign all its neighbors to even
      - Remove both sets from the pool and repeat until done

    NOTE: This is not a true bipartite coloring (triangles create odd cycles),
    but it matches your original intent and behavior.

    Returns:
        even_indices, odd_indices   (both 1D np.int64 arrays, sorted unique)
    """
    if seed is not None:
        rng = np.random.default_rng(seed)
    else:
        rng = np.random.default_rng()

    # Build adjacency list from faces
    neighbors = [set() for _ in range(n_vertices)]
    for a, b, c in faces:
        neighbors[a].update([b, c])
        neighbors[b].update([a, c])
        neighbors[c].update([a, b])

    unassigned = set(range(n_vertices))
    even_set, odd_set = set(), set()

    while unassigned:
        # Select a random vertex
        curr = rng.choice(list(unassigned))
        odd_set.add(curr)

        neigh = neighbors[curr]
        even_set.update(neigh)

        # Remove current and its neighbors from pool
        unassigned.discard(curr)
        for nb in neigh:
            unassigned.discard(nb)

    # Ensure sets are disjoint (they should be by construction)
    even_only = np.array(sorted(even_set - odd_set), dtype=np.int64)
    odd_only = np.array(sorted(odd_set - even_set), dtype=np.int64)
    return even_only, odd_only

def poisson_reconstruct_from_points(
    points: np.ndarray,
    normals: np.ndarray,
    depth: int = 9,
    trim_percentile: Optional[float] = 2.0,
    keep_largest_component: bool = True,
) -> o3d.geometry.TriangleMesh:
    """
    Run Poisson reconstruction on a point cloud with known outward normals, then clean.

    Args:
        points: (N, 3)
        normals: (N, 3) outward normals (do NOT re-estimate)
        depth: Poisson octree depth
        trim_percentile: if set (e.g., 2.0), trims lowest-density vertices at that percentile
        keep_largest_component: if True, keep only the largest triangle cluster
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points.astype(np.float64))
    pcd.normals = o3d.utility.Vector3dVector(_normalize_rows(normals))

    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=depth, width=0, scale=1.1, linear_fit=False)
    densities = np.asarray(densities)

    # Optional: density-based trimming to remove thin artifacts
    # if trim_percentile is not None:
    #     thr = np.percentile(densities, trim_percentile)
    #     verts_to_remove = densities < thr
    #     mesh.remove_vertices_by_mask(verts_to_remove)

    # Clean up mesh
    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles()
    mesh.remove_non_manifold_edges()

    if keep_largest_component and len(mesh.triangles) > 0:
        clusters, n_tris, _ = mesh.cluster_connected_triangles()
        clusters = np.asarray(clusters)
        n_tris = np.asarray(n_tris)
        if n_tris.size > 0:
            largest_id = n_tris.argmax()
            mask = clusters != largest_id
            mesh.remove_triangles_by_mask(mask)

    # Final normals on the reconstructed watertight mesh
    mesh.paint_uniform_color([1, 0.706, 0])
    mesh.compute_triangle_normals()
    mesh.orient_triangles()      # ensure global consistent face orientation
    mesh.compute_vertex_normals()

    return mesh

# ---------------------------
# Main API
# ---------------------------

def mesh_smoothing(
    file_path: str,
    poisson_depth: int,
    save_path: str,
    save_file_name: str,
    keep: str = "even",
    seed: Optional[int] = 0,
    trim_percentile: Optional[float] = 2.0,
    visualize: bool = False,
) -> str:
    """
    End-to-end mesh smoothing:
      1) Read STL with correct facet normals
      2) Compute vertex normals by area-weighted averaging
      3) Reduce vertices via odd/even partition (like original)
      4) Poisson reconstruction using preserved outward normals
      5) Save STL

    Args:
        file_path: input STL path
        poisson_depth: octree depth for Poisson (typical 8–12)
        save_path: output directory
        save_file_name: file name without extension
        keep: 'even' or 'odd' (which group to keep after partition)
        seed: RNG seed for reproducibility (partition randomness)
        trim_percentile: density trim (None to disable)
        visualize: if True, shows intermediate visualizations in Open3D windows

    Returns:
        out_path: path to saved STL
    """
    # --- Step 1: Read STL, get vertices, faces, and facet normals ---
    vertices, faces, facet_normals = read_stl_unique(file_path)

    if visualize:
        orig = o3d.geometry.TriangleMesh(
            o3d.utility.Vector3dVector(vertices),
            o3d.utility.Vector3iVector(faces),
        )
        orig.compute_vertex_normals()
        o3d.visualization.draw_geometries([orig], window_name="Original Mesh", 
                                          width=800, height=800)

    # --- Step 2: Vertex normals from facet normals (area-weighted) ---
    vertex_normals = compute_vertex_normals_from_facets(vertices, faces, facet_normals, weight="area")

    # --- Step 3: Odd/Even partition like the original logic ---
    even_idx, odd_idx = greedy_even_odd_partition(faces, n_vertices=vertices.shape[0], seed=seed)

    if keep.lower() not in ("even", "odd"):
        raise ValueError("keep must be 'even' or 'odd'")
    keep_idx = even_idx if keep.lower() == "even" else odd_idx

    points_reduced = vertices[keep_idx]
    normals_reduced = vertex_normals[keep_idx]

    if visualize:
        pcd_vis = o3d.geometry.PointCloud()
        pcd_vis.points = o3d.utility.Vector3dVector(points_reduced)
        pcd_vis.normals = o3d.utility.Vector3dVector(normals_reduced)
        o3d.visualization.draw_geometries(
            [pcd_vis], point_show_normal=True, window_name=f"Reduced points ({keep}), with normals", 
                                              width=800, height=800)

    # --- Step 4: Poisson reconstruction using the preserved outward normals ---
    mesh_poisson = poisson_reconstruct_from_points(
        points_reduced,
        normals_reduced,
        depth=poisson_depth,
        trim_percentile=trim_percentile,
        keep_largest_component=True,
    )

    if visualize:
        o3d.visualization.draw_geometries([mesh_poisson], window_name="Poisson Reconstruction (cleaned)", 
                                          width=800, height=800)

    # --- Step 5: Save STL ---
    os.makedirs(save_path, exist_ok=True)
    out_path = os.path.join(save_path, f"{save_file_name}.stl")
    o3d.io.write_triangle_mesh(out_path, mesh_poisson, write_ascii=False)
    print(f"Saved: {out_path}")
    return out_path

# ---------------------------
# Example usage (uncomment to run as script)
# ---------------------------
# if __name__ == "__main__":
#     mesh_smoothing(
#         file_path="B:/Projekte/bhejazi/VHCF/XCT_analysis/contact-point-stats/Oct24-n3/Contour Mesh Of defect-drop3.stl",
#         poisson_depth=7,
#         save_path="B:/Projekte/bhejazi/VHCF/XCT_analysis/contact-point-stats/Oct24-n3",
#         save_file_name="smoothed_mesh-new-test2",
#         keep="even",        # or "odd"
#         seed=0,
#         trim_percentile=2.0,
#         visualize=True,
#     )
