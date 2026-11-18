import unittest

from measure_paths import crossing, dist, projection, shortest


class GraphTests(unittest.TestCase):
    def test_intersection_and_projection(self):
        self.assertEqual(crossing((0, 0), (10, 0), (5, -2), (5, 2)), (5, 0))
        self.assertIsNone(crossing((0, 0), (10, 0), (11, -2), (11, 2)))
        self.assertEqual(projection((4, 3), (0, 0), (10, 0)), (4, 0))
        self.assertEqual(projection((12, 3), (0, 0), (10, 0)), (10, 0))
        self.assertEqual(dist((0, 0), (3, 4)), 5)

    def test_shortest_and_disconnected(self):
        graph = {
            "a": [("b", 2, "track"), ("c", 10, "track")],
            "b": [("c", 3, "via")],
            "c": [],
        }
        length, path = shortest(graph, "a", {"c"})
        self.assertEqual(length, 5)
        self.assertEqual(path, [("b", "track"), ("c", "via")])
        self.assertIsNone(shortest(graph, "a", {"d"}))


if __name__ == "__main__":
    unittest.main()
