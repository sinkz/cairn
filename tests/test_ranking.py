from __future__ import annotations

import unittest

from cairn.ranking import fts_query_variants, query_tokens, rrf_merge


class RankingTests(unittest.TestCase):
    def test_query_tokens_strip_field_prefixes_and_operators(self) -> None:
        self.assertEqual(
            query_tokens("title:deploy AND token body:rotation"),
            ("deploy", "token", "rotation"),
        )

    def test_fts_query_variants_include_safe_prefix_variant(self) -> None:
        self.assertEqual(
            fts_query_variants("deploy token rotation kubernetes secret"),
            [
                '"deploy" "token" "rotation" "kubernetes" "secret"',
                '"deploy" OR "token" OR "rotation" OR "kubernetes" OR "secret"',
                "deploy* OR token* OR rotat* OR kubernetes* OR secret*",
            ],
        )

    def test_fts_query_variants_skip_unsafe_prefix_terms(self) -> None:
        self.assertEqual(
            fts_query_variants("ci JWT 403 db rotating"),
            [
                '"ci" "JWT" "403" "db" "rotating"',
                '"ci" OR "JWT" OR "403" OR "db" OR "rotating"',
                "rotat*",
            ],
        )

    def test_rrf_merge_is_deterministic(self) -> None:
        runs = [
            ["doc-a", "doc-b", "doc-c"],
            ["doc-b", "doc-a", "doc-d"],
            ["doc-a", "doc-d", "doc-b"],
        ]

        self.assertEqual(rrf_merge(runs, k=60), ["doc-a", "doc-b", "doc-d", "doc-c"])

    def test_rrf_merge_keeps_first_seen_order_for_exact_ties(self) -> None:
        runs = [
            ["doc-b", "doc-a"],
            ["doc-a", "doc-b"],
        ]

        self.assertEqual(rrf_merge(runs, k=60), ["doc-b", "doc-a"])

    def test_rrf_merge_ignores_duplicate_ids_within_same_run(self) -> None:
        runs = [
            ["doc-a", "doc-a", "doc-b"],
            ["doc-b"],
        ]

        self.assertEqual(rrf_merge(runs, k=60), ["doc-b", "doc-a"])


if __name__ == "__main__":
    unittest.main()
