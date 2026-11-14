import unittest

from pagerank import pagerank


class TestPageRank(unittest.TestCase):

    def test_rank_sum(self):
        graph = [
            {1, 2},
            {2},
            set()
        ]

        ranks = pagerank(graph, iterations=100)

        self.assertEqual(len(ranks), 3)
        self.assertAlmostEqual(sum(ranks), 1.0, places=6)

    def test_dangling_page(self):
        graph = [
            {1},
            set()
        ]

        ranks = pagerank(graph, iterations=100)

        self.assertAlmostEqual(sum(ranks), 1.0, places=6)

    def test_disconnected_graph(self):
        graph = [
            {1},
            {0},
            {3},
            {2}
        ]

        ranks = pagerank(graph, iterations=100)

        self.assertEqual(len(ranks), 4)
        self.assertAlmostEqual(sum(ranks), 1.0, places=6)

        for rank in ranks:
            self.assertAlmostEqual(rank, 0.25, places=6)

if __name__ == "__main__":
    unittest.main()
