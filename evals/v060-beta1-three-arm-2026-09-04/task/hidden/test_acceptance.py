import unittest

from src.tag_index import merge_tags


class HiddenAcceptanceTests(unittest.TestCase):
    def test_normalizes_and_preserves_first_seen_order(self):
        existing = ["  Beta ", "ALPHA", "", "beta"]
        incoming = [" alpha ", "Gamma", "  ", "DELTA", "gamma"]
        self.assertEqual(merge_tags(existing, incoming), ["Beta", "ALPHA", "Gamma", "DELTA"])

    def test_does_not_mutate_list_inputs(self):
        existing = [" One ", "TWO"]
        incoming = ["two", "Three"]
        original_existing = list(existing)
        original_incoming = list(incoming)
        merge_tags(existing, incoming)
        self.assertEqual(existing, original_existing)
        self.assertEqual(incoming, original_incoming)

    def test_accepts_one_shot_iterables(self):
        existing = (value for value in [" One ", "TWO"])
        incoming = (value for value in ["two", "Three"])
        self.assertEqual(merge_tags(existing, incoming), ["One", "TWO", "Three"])


if __name__ == "__main__":
    unittest.main()
