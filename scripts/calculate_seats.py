#!/usr/bin/env python3
"""Estimate Baden-Wuerttemberg Landtag seats from StatLA data."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import poll_election_core as core


BASE_SEAT_COUNT = 120


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate the seat distribution for Baden-Wuerttemberg under the "
            "current two-vote law from StatLA data."
        )
    )
    parser.add_argument(
        "--election-key",
        default=core.DEFAULT_ELECTION_KEY,
        help="Election key in YEAR-STATE format (default: %(default)s).",
    )
    parser.add_argument(
        "--source",
        choices=("latest", "live"),
        default="latest",
        help="Use tracked latest exports or fetch fresh StatLA data (default: %(default)s).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text table.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show fetch progress when using --source live.",
    )
    return parser.parse_args()


def load_run_metadata() -> Dict[str, Any]:
    path = core.LATEST_DIR / "run_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_statla_state(config: core.Config, source: str, verbose: bool) -> Dict[str, Any]:
    if source == "live":
        core.set_cli_feedback(verbose=verbose, progress=verbose)
        return core.fetch_statla(config, timeout_seconds=config.request_timeout_seconds)
    latest = core.load_latest_statla_exports()
    metadata = load_run_metadata()
    return {
        "mode": metadata.get("statla_mode", "LATEST"),
        "url": metadata.get("statla_url", config.statla_live_csv_url),
        "snapshots": latest.get("snapshots", []),
        "party_rows": latest.get("party_rows", []),
        "error_message": metadata.get("statla_error"),
    }


def land_snapshot_row(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    for row in rows:
        if str(row.get("gebietsart") or "") == "LAND":
            return row
    raise ValueError("No LAND row found in StatLA snapshots")


def land_second_vote_totals(party_rows: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for row in party_rows:
        if not str(row.get("row_key") or "").endswith(":LAND"):
            continue
        if core.canonical_vote_type(row.get("vote_type")) != "Zweitstimmen":
            continue
        party = core.canonical_party_name(row.get("party_name"), "Zweitstimmen")
        votes = core.parse_int(row.get("votes")) or 0
        if party and votes:
            totals[party] = totals.get(party, 0) + votes
    return totals


def wahlkreis_rows_by_key(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("gebietsart") or "") != "WAHLKREIS":
            continue
        output[str(row.get("row_key") or "")] = row
    return output


def direct_winners(
    snapshots: List[Dict[str, Any]],
    party_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    wahlkreise = wahlkreis_rows_by_key(snapshots)
    first_votes: Dict[str, Dict[str, int]] = defaultdict(dict)
    for row in party_rows:
        row_key = str(row.get("row_key") or "")
        if row_key not in wahlkreise:
            continue
        if core.canonical_vote_type(row.get("vote_type")) != "Erststimmen":
            continue
        party = core.canonical_party_name(row.get("party_name"), "Erststimmen")
        votes = core.parse_int(row.get("votes")) or 0
        if party:
            first_votes[row_key][party] = votes

    winners: List[Dict[str, Any]] = []
    for row_key, votes_by_party in first_votes.items():
        if not votes_by_party:
            continue
        winner_party, winner_votes = max(votes_by_party.items(), key=lambda item: (item[1], item[0]))
        wahlkreis = wahlkreise[row_key]
        winners.append(
            {
                "row_key": row_key,
                "wahlkreis_nummer": str(wahlkreis.get("gebietsnummer") or ""),
                "wahlkreis_name": str(wahlkreis.get("municipality_name") or ""),
                "winner_party": winner_party,
                "winner_votes": winner_votes,
            }
        )
    winners.sort(key=lambda row: int(row["wahlkreis_nummer"]))
    return winners


def sainte_lague(votes: Dict[str, int], seat_count: int) -> Dict[str, int]:
    quotients: List[Tuple[float, str]] = []
    for party, vote_total in votes.items():
        for divisor in range(1, 2 * seat_count, 2):
            quotients.append((vote_total / divisor, party))
    quotients.sort(reverse=True)
    allocation: Counter[str] = Counter()
    for _value, party in quotients[:seat_count]:
        allocation[party] += 1
    return dict(allocation)


def find_minimum_house_size(votes: Dict[str, int], direct_counts: Dict[str, int]) -> Tuple[int, Dict[str, int]]:
    for seat_count in range(BASE_SEAT_COUNT, 400):
        allocation = sainte_lague(votes, seat_count)
        if all(allocation.get(party, 0) >= direct_counts.get(party, 0) for party in direct_counts):
            return seat_count, allocation
    raise RuntimeError("No seat allocation found up to 399 seats")


def estimate_bw_seats(statla: Dict[str, Any]) -> Dict[str, Any]:
    snapshots = statla.get("snapshots", [])
    party_rows = statla.get("party_rows", [])
    if not snapshots or not party_rows:
        raise RuntimeError("No StatLA snapshot data available")

    land_row = land_snapshot_row(snapshots)
    valid_second_votes = core.parse_int(land_row.get("valid_votes_zweit")) or 0
    if valid_second_votes <= 0:
        raise RuntimeError("No valid statewide second votes available")

    second_votes = land_second_vote_totals(party_rows)
    eligible_votes = {
        party: votes
        for party, votes in second_votes.items()
        if valid_second_votes and (votes / valid_second_votes) >= 0.05
    }
    winners = direct_winners(snapshots, party_rows)
    direct_counts = Counter(row["winner_party"] for row in winners)

    non_eligible_winners = {
        party: count
        for party, count in direct_counts.items()
        if party not in eligible_votes
    }
    seat_count, allocation = find_minimum_house_size(eligible_votes, dict(direct_counts))

    party_rows_out: List[Dict[str, Any]] = []
    eligible_vote_total = sum(eligible_votes.values())
    for party in sorted(allocation, key=lambda name: (-allocation[name], name)):
        second_vote_total = eligible_votes[party]
        seats = allocation[party]
        direct = direct_counts.get(party, 0)
        party_rows_out.append(
            {
                "party": party,
                "second_votes": second_vote_total,
                "second_vote_share_valid": (second_vote_total / valid_second_votes) * 100,
                "second_vote_share_eligible": (second_vote_total / eligible_vote_total) * 100 if eligible_vote_total else 0.0,
                "seats": seats,
                "direct_seats": direct,
                "list_seats": seats - direct,
            }
        )

    return {
        "source_mode": statla.get("mode"),
        "source_url": statla.get("url"),
        "source_error": statla.get("error_message"),
        "reported_precincts": core.parse_int(land_row.get("reported_precincts")) or 0,
        "total_precincts": core.parse_int(land_row.get("total_precincts")) or 0,
        "valid_second_votes": valid_second_votes,
        "eligible_parties": len(eligible_votes),
        "base_seats": BASE_SEAT_COUNT,
        "total_seats": seat_count,
        "compensation_seats": seat_count - BASE_SEAT_COUNT,
        "party_rows": party_rows_out,
        "direct_winners": winners,
        "direct_counts": dict(direct_counts),
        "non_eligible_direct_winners": non_eligible_winners,
        "notes": [
            "This matches the official BW two-vote logic at party level: 5% threshold, direct winners kept, Sainte-Lague/Schepers allocation from second votes, and additional seats until every qualifying party covers its direct mandates.",
            "If a successful direct winner belonged to a party below 5% or without a state list, the law excludes a subset of second votes that cannot be reconstructed from aggregated CSV data alone.",
        ],
    }


def print_text(result: Dict[str, Any]) -> None:
    print(f"Source mode: {result['source_mode']}")
    print(f"Source URL: {result['source_url']}")
    if result.get("source_error"):
        print(f"Source note: {result['source_error']}")
    print(
        "Counted precincts: "
        f"{result['reported_precincts']:,}/{result['total_precincts']:,}"
    )
    print(f"Valid second votes: {result['valid_second_votes']:,}")
    print(
        "Estimated house size: "
        f"{result['total_seats']} ({result['compensation_seats']} above the 120 base seats)"
    )
    print("")
    print("Party           Votes       Share(valid)  Seats  Direct  List")
    print("-------------------------------------------------------------")
    for row in result["party_rows"]:
        print(
            f"{row['party']:<15}"
            f"{row['second_votes']:>10,}  "
            f"{row['second_vote_share_valid']:>11.3f}%  "
            f"{row['seats']:>5}  "
            f"{row['direct_seats']:>6}  "
            f"{row['list_seats']:>4}"
        )
    print("")
    print("Direct mandates by party:")
    for party, count in sorted(result["direct_counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {party}: {count}")
    if result["non_eligible_direct_winners"]:
        print("")
        print("Warning: direct winners outside the 5% group were detected.")
        for party, count in sorted(result["non_eligible_direct_winners"].items(), key=lambda item: (-item[1], item[0])):
            print(f"  {party}: {count}")


def main() -> None:
    args = parse_args()
    core.set_active_election(election_key=args.election_key)
    config = core.load_config()
    state_code = config.election_key.rsplit("-", 1)[-1].lower()
    if state_code != "bw":
        raise SystemExit("Seat calculation is currently implemented only for Baden-Wuerttemberg elections.")

    statla = load_statla_state(config, args.source, args.verbose)
    result = estimate_bw_seats(statla)

    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return
    print_text(result)


if __name__ == "__main__":
    main()
