#!/usr/bin/env python3
"""Calculate RLP landtag seats from a structured JSON input."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from rlp_seat_allocation import calculate_rlp_seats, example_input_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to a structured RLP seat input JSON file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text table.",
    )
    parser.add_argument(
        "--print-example",
        action="store_true",
        help="Print an example input JSON payload and exit.",
    )
    return parser.parse_args()


def load_payload(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def print_text(result: Dict[str, Any]) -> None:
    print(f"Status: {result['status']}")
    if result.get("source_label"):
        print(f"Source: {result['source_label']}")
    print(f"Valid Landesstimmen: {result['valid_list_votes']:,}")
    print(f"Threshold (5%): {result['threshold_votes_min']:,} votes")

    if result["status"] != "ok":
        print("")
        for note in result.get("notes", []):
            print(f"- {note}")
        return

    print(f"Base seats: {result['base_seats']}")
    print(f"Total seats after balance: {result['total_seats']}")
    print(f"Balance seats: {result['balance_seats']}")
    if result.get("majority_bonus_party"):
        print(f"Majority safeguard applied: {result['majority_bonus_party']}")
    print("")
    print(f"{'Party':<24} {'Votes':>12} {'Share':>8} {'Direct':>7} {'List':>5} {'Seats':>5}")
    print("-------------------------------------------------------------------")
    for row in result["party_rows"]:
        print(
            f"{row['party']:<24}"
            f"{row['votes']:>12,} "
            f"{row['vote_share_valid_percent']:>7.2f}% "
            f"{row['direct_mandates']:>7} "
            f"{row['list_seats']:>5} "
            f"{row['total_seats']:>5}"
        )
        if row["list_type"] == "district":
            for list_row in row.get("lists", []):
                label = list_row["label"]
                print(
                    f"  {label:<22}"
                    f"{list_row['votes']:>12,} "
                    f"{list_row['vote_share_party_percent']:>7.2f}% "
                    f"{list_row['direct_mandates']:>7} "
                    f"{list_row['list_seats']:>5} "
                    f"{list_row['total_seats']:>5}"
                )

    if result.get("notes"):
        print("")
        for note in result["notes"]:
            print(f"- {note}")


def main() -> int:
    args = parse_args()
    if args.print_example:
        print(json.dumps(example_input_payload(), indent=2, ensure_ascii=False))
        return 0
    if args.input is None:
        raise SystemExit("Pass --input <path> or use --print-example")

    result = calculate_rlp_seats(load_payload(args.input))
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
