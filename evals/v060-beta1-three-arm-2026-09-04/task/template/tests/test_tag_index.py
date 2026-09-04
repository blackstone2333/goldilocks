import unittest

from src.tag_index import merge_tags


class MergeTagsTests(unittest.TestCase):
    def test_combines_unique_tags(self):
        self.assertEqual(merge_tags(["alpha"], ["beta", "alpha"]), ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
