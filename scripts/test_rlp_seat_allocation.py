#!/usr/bin/env python3
"""Lightweight self-tests for the RLP seat allocation helpers."""

from __future__ import annotations

from rlp_seat_allocation import calculate_rlp_seats


def test_majority_safeguard() -> None:
    result = calculate_rlp_seats(
        {
            "source_label": "majority safeguard",
            "base_seats": 4,
            "parties": [
                {"party": "A", "list_type": "land", "votes": 51},
                {"party": "B", "list_type": "land", "votes": 49},
            ],
        }
    )
    assert result["status"] == "ok"
    assert result["total_seats"] == 4
    assert result["majority_bonus_party"] == "A"
    seats_by_party = {row["party"]: row["total_seats"] for row in result["party_rows"]}
    assert seats_by_party == {"A": 3, "B": 1}


def test_overhang_balance_without_majority_party() -> None:
    result = calculate_rlp_seats(
        {
            "source_label": "overhang balance",
            "base_seats": 5,
            "parties": [
                {"party": "A", "list_type": "land", "votes": 49, "direct_mandates": 4},
                {"party": "B", "list_type": "land", "votes": 33},
                {"party": "C", "list_type": "land", "votes": 18},
            ],
        }
    )
    assert result["status"] == "ok"
    assert result["majority_bonus_party"] is None
    assert result["total_seats"] == 7
    seats_by_party = {row["party"]: row["total_seats"] for row in result["party_rows"]}
    assert seats_by_party == {"A": 4, "B": 2, "C": 1}


def test_district_list_suballocation() -> None:
    result = calculate_rlp_seats(
        {
            "source_label": "district lists",
            "base_seats": 6,
            "parties": [
                {
                    "party": "A",
                    "list_type": "district",
                    "lists": [
                        {"list_id": "A-1", "label": "Bezirk 1", "votes": 60, "direct_mandates": 2},
                        {"list_id": "A-2", "label": "Bezirk 2", "votes": 40, "direct_mandates": 0},
                    ],
                },
                {"party": "B", "list_type": "land", "votes": 80},
            ],
        }
    )
    assert result["status"] == "ok"
    party_rows = {row["party"]: row for row in result["party_rows"]}
    assert result["majority_bonus_party"] == "A"
    assert party_rows["A"]["total_seats"] == 4
    list_rows = {row["list_id"]: row for row in party_rows["A"]["lists"]}
    assert list_rows["A-1"]["total_seats"] == 2
    assert list_rows["A-2"]["total_seats"] == 2


def test_below_threshold_direct_winner_is_rejected() -> None:
    try:
        calculate_rlp_seats(
            {
                "source_label": "unsupported direct winner",
                "base_seats": 5,
                "parties": [
                    {"party": "A", "list_type": "land", "votes": 96},
                    {"party": "B", "list_type": "land", "votes": 4, "direct_mandates": 1},
                ],
            }
        )
    except ValueError as exc:
        assert "bereinigte Landesstimmen" in str(exc)
        return
    raise AssertionError("Expected unsupported direct-winner edge case to raise ValueError")


def main() -> int:
    test_majority_safeguard()
    test_overhang_balance_without_majority_party()
    test_district_list_suballocation()
    test_below_threshold_direct_winner_is_rejected()
    print("RLP seat allocation self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
