from __future__ import annotations

import unittest

import numpy as np

from windfarm_moe.graph import build_dynamic_graph, build_haversine_gaussian_graph, build_static_candidates, haversine_distance_km


class GraphBuilderTests(unittest.TestCase):
    def test_wind_direction_flips_edge_direction(self) -> None:
        coords = np.array([[0.0, 0.0], [500.0, 0.0], [1000.0, 0.0]], dtype=np.float32)
        candidates = build_static_candidates(coords, candidate_k=2, max_distance=1500.0)

        west_to_east = np.full((1, 3), 270.0, dtype=np.float32)
        east_to_west = np.full((1, 3), 90.0, dtype=np.float32)

        idx_we, _, _ = build_dynamic_graph(
            west_to_east,
            candidates,
            max_in_edges=2,
            cone_half_angle_deg=25.0,
            parallel_scale=1200.0,
            cross_scale=400.0,
            direction_is_from=True,
            chunk_size=1,
        )
        idx_ew, _, _ = build_dynamic_graph(
            east_to_west,
            candidates,
            max_in_edges=2,
            cone_half_angle_deg=25.0,
            parallel_scale=1200.0,
            cross_scale=400.0,
            direction_is_from=True,
            chunk_size=1,
        )

        incoming_to_middle_we = set(idx_we[0, 1][idx_we[0, 1] >= 0].tolist())
        incoming_to_middle_ew = set(idx_ew[0, 1][idx_ew[0, 1] >= 0].tolist())
        self.assertIn(0, incoming_to_middle_we)
        self.assertIn(2, incoming_to_middle_ew)
        self.assertNotEqual(incoming_to_middle_we, incoming_to_middle_ew)

    def test_haversine_distance_and_gaussian_graph(self) -> None:
        coords = np.array(
            [
                [30.0, 120.0],
                [30.0, 120.1],
                [30.0, 120.2],
                [30.1, 120.0],
            ],
            dtype=np.float32,
        )
        distances = haversine_distance_km(coords)
        self.assertAlmostEqual(float(distances[0, 0]), 0.0, places=4)
        self.assertAlmostEqual(float(distances[0, 1]), float(distances[1, 0]), places=4)
        self.assertLess(float(distances[0, 1]), float(distances[0, 2]))

        edge_index, edge_weight, meta = build_haversine_gaussian_graph(coords, candidate_k=2)
        self.assertGreater(meta["sigma_km"], 0.0)
        node0_neighbors = edge_index[0][edge_index[0] >= 0]
        self.assertGreaterEqual(node0_neighbors.size, 2)
        neighbor_to_weight = {
            int(neighbor): float(weight)
            for neighbor, weight in zip(edge_index[0], edge_weight[0])
            if neighbor >= 0
        }
        self.assertGreater(neighbor_to_weight[1], neighbor_to_weight[2])


if __name__ == "__main__":
    unittest.main()
