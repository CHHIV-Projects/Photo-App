"""Unit tests for duplicate suggestion deterministic helpers."""

from __future__ import annotations

import unittest

from app.services.duplicates.suggestion_service import _canonical_pair, confidence_bucket_for_distance


class DuplicateSuggestionServiceTests(unittest.TestCase):
    def test_confidence_bucket_ranges(self) -> None:
        self.assertEqual(confidence_bucket_for_distance(0), "high")
        self.assertEqual(confidence_bucket_for_distance(5), "high")
        self.assertEqual(confidence_bucket_for_distance(6), "medium")
        self.assertEqual(confidence_bucket_for_distance(10), "medium")
        self.assertEqual(confidence_bucket_for_distance(11), "low")
        self.assertEqual(confidence_bucket_for_distance(15), "low")
        self.assertIsNone(confidence_bucket_for_distance(16))

    def test_canonical_pair_is_symmetric(self) -> None:
        self.assertEqual(_canonical_pair("a", "b"), ("a", "b"))
        self.assertEqual(_canonical_pair("b", "a"), ("a", "b"))


if __name__ == "__main__":
    unittest.main()
