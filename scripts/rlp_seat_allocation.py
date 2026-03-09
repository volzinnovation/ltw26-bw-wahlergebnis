#!/usr/bin/env python3
"""Seat allocation helpers for Rheinland-Pfalz landtag elections.

This module implements the core legal steps from the official 2026 RLP
Wahlsystem description and LWahlG sections 29 to 31:

- 101 nominal seats by default
- 5% threshold on valid Landesstimmen
- Sainte-Lague/Schepers seat allocation
- the majority-seat safeguard from LWahlG 29(3)
- overhang retention plus house-size expansion until balanced
- optional Bezirkslisten with statewide list connections

The allocator consumes a small structured JSON payload instead of scraping a
specific result portal. That keeps the law implementation separate from future
RLP result-source adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_BASE_SEATS = 101
MAX_TOTAL_SEATS = 1000
THRESHOLD = Fraction(5, 100)


def parse_int(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip()
    if not text:
        return 0
    text = text.replace(".", "").replace(" ", "").replace("\u00a0", "")
    return int(text)


@dataclass(frozen=True)
class ListUnit:
    list_id: str
    label: str
    votes: int
    direct_mandates: int
    district_id: str
    district_name: str


@dataclass(frozen=True)
class PartyInput:
    party: str
    list_type: str
    list_units: Tuple[ListUnit, ...]
    unattached_direct_mandates: int = 0

    @property
    def total_votes(self) -> int:
        return sum(unit.votes for unit in self.list_units)

    @property
    def total_direct_mandates(self) -> int:
        return self.unattached_direct_mandates + sum(unit.direct_mandates for unit in self.list_units)


def _make_list_unit(raw: Dict[str, Any], *, fallback_id: str, fallback_label: str) -> ListUnit:
    list_id = str(raw.get("list_id") or raw.get("district_id") or fallback_id).strip()
    if not list_id:
        raise ValueError("Every RLP list unit requires a non-empty list_id")
    label = str(raw.get("label") or raw.get("district_name") or fallback_label).strip() or list_id
    return ListUnit(
        list_id=list_id,
        label=label,
        votes=parse_int(raw.get("votes")),
        direct_mandates=parse_int(raw.get("direct_mandates")),
        district_id=str(raw.get("district_id") or "").strip(),
        district_name=str(raw.get("district_name") or "").strip(),
    )


def normalize_party_inputs(payload: Dict[str, Any]) -> List[PartyInput]:
    parties_raw = payload.get("parties")
    if not isinstance(parties_raw, list) or not parties_raw:
        raise ValueError("RLP seat input requires a non-empty 'parties' array")

    parties: List[PartyInput] = []
    for index, raw_party in enumerate(parties_raw, start=1):
        if not isinstance(raw_party, dict):
            raise ValueError(f"Party entry #{index} must be an object")
        party = str(raw_party.get("party") or raw_party.get("label") or "").strip()
        if not party:
            raise ValueError(f"Party entry #{index} is missing 'party'")

        list_type = str(raw_party.get("list_type") or "land").strip().lower()
        if list_type not in {"land", "district", "none"}:
            raise ValueError(
                f"Party '{party}' has unsupported list_type {list_type!r}; expected 'land', 'district', or 'none'"
            )

        raw_lists = raw_party.get("lists")
        if list_type == "none":
            if raw_lists:
                raise ValueError(f"Party '{party}' uses list_type 'none' but still defines 'lists'")
            if parse_int(raw_party.get("votes")):
                raise ValueError(f"Party '{party}' uses list_type 'none' but still defines list votes")
            parties.append(
                PartyInput(
                    party=party,
                    list_type=list_type,
                    list_units=(),
                    unattached_direct_mandates=parse_int(raw_party.get("direct_mandates")),
                )
            )
            continue

        if list_type == "land":
            if raw_lists:
                if not isinstance(raw_lists, list) or len(raw_lists) != 1 or not isinstance(raw_lists[0], dict):
                    raise ValueError(f"Party '{party}' with list_type 'land' requires exactly one list object")
                unit = _make_list_unit(raw_lists[0], fallback_id=party, fallback_label=party)
            else:
                unit = _make_list_unit(
                    {
                        "list_id": raw_party.get("list_id") or party,
                        "label": raw_party.get("label") or party,
                        "votes": raw_party.get("votes"),
                        "direct_mandates": raw_party.get("direct_mandates"),
                    },
                    fallback_id=party,
                    fallback_label=party,
                )
            parties.append(PartyInput(party=party, list_type=list_type, list_units=(unit,)))
            continue

        if not isinstance(raw_lists, list) or not raw_lists:
            raise ValueError(f"Party '{party}' with list_type 'district' requires a non-empty 'lists' array")
        units: List[ListUnit] = []
        for list_index, raw_list in enumerate(raw_lists, start=1):
            if not isinstance(raw_list, dict):
                raise ValueError(f"Party '{party}' list #{list_index} must be an object")
            units.append(
                _make_list_unit(
                    raw_list,
                    fallback_id=f"{party}-{list_index}",
                    fallback_label=f"{party} list {list_index}",
                )
            )
        parties.append(PartyInput(party=party, list_type=list_type, list_units=tuple(units)))

    seen_parties: set[str] = set()
    for party in parties:
        if party.party in seen_parties:
            raise ValueError(f"Duplicate party key in RLP seat input: {party.party}")
        seen_parties.add(party.party)
    return parties


def threshold_votes_min(valid_votes: int) -> int:
    return (valid_votes * 5 + 99) // 100


def vote_share_percent(votes: int, total_votes: int) -> float:
    if total_votes <= 0:
        return 0.0
    return (votes / total_votes) * 100.0


def top_level_vote_map(parties: Iterable[PartyInput]) -> Dict[str, int]:
    return {party.party: party.total_votes for party in parties}


def highest_averages_allocation(votes: Dict[str, int], seat_count: int) -> Dict[str, int]:
    if seat_count < 0:
        raise ValueError("seat_count must not be negative")
    allocation = {key: 0 for key in votes}
    if seat_count == 0 or not votes:
        return allocation

    quotients: List[Tuple[Fraction, str]] = []
    for key, vote_total in votes.items():
        if vote_total < 0:
            raise ValueError(f"Negative vote total for {key!r}")
        for seat_index in range(seat_count):
            quotients.append((Fraction(vote_total * 2, 2 * seat_index + 1), key))
    quotients.sort(key=lambda item: (item[0], item[1]), reverse=True)

    if seat_count < len(quotients) and quotients[seat_count - 1][0] == quotients[seat_count][0]:
        raise ValueError("Exact Sainte-Lague tie at the final seat boundary; official lot result required")

    for quotient, key in quotients[:seat_count]:
        if quotient <= 0:
            continue
        allocation[key] += 1
    return allocation


def apply_majority_rule(votes: Dict[str, int], seat_count: int) -> Tuple[Dict[str, int], Optional[str]]:
    if seat_count <= 0 or not votes:
        return {key: 0 for key in votes}, None

    total_votes = sum(votes.values())
    majority_party = next(
        (
            key
            for key, vote_total in votes.items()
            if vote_total > 0 and Fraction(vote_total, total_votes) > Fraction(1, 2)
        ),
        None,
    )
    regular = highest_averages_allocation(votes, seat_count)
    if majority_party is None:
        return regular, None
    if regular.get(majority_party, 0) > seat_count / 2:
        return regular, None

    adjusted = highest_averages_allocation(votes, seat_count - 1)
    adjusted[majority_party] = adjusted.get(majority_party, 0) + 1
    if adjusted.get(majority_party, 0) <= seat_count / 2:
        raise RuntimeError(f"Majority safeguard failed for {majority_party!r}")
    return adjusted, majority_party


def allocate_party_list_units(party: PartyInput, party_seat_count: int) -> Dict[str, int]:
    if party.list_type == "land":
        if not party.list_units:
            return {}
        return {party.list_units[0].list_id: party_seat_count}
    if party.list_type == "district":
        return highest_averages_allocation({unit.list_id: unit.votes for unit in party.list_units}, party_seat_count)
    return {}


def _unsupported_direct_mandates(parties: Iterable[PartyInput], qualifying_parties: Dict[str, int]) -> List[str]:
    unsupported: List[str] = []
    for party in parties:
        if party.total_direct_mandates <= 0:
            continue
        if party.list_type == "none" or party.party not in qualifying_parties:
            unsupported.append(party.party)
    return sorted(unsupported)


def _validate_direct_mandate_inputs(parties: Iterable[PartyInput]) -> None:
    for party in parties:
        if party.total_direct_mandates > 0 and party.total_votes <= 0:
            raise ValueError(
                f"Party '{party.party}' has direct mandates but no positive Landesstimmen. "
                "This cannot be balanced from aggregate list-vote totals."
            )
        for unit in party.list_units:
            if unit.direct_mandates > 0 and unit.votes <= 0:
                raise ValueError(
                    f"Party '{party.party}' list '{unit.list_id}' has direct mandates but no positive Landesstimmen."
                )


def build_party_rows(
    parties: Iterable[PartyInput],
    *,
    valid_votes: int,
    qualifying_vote_total: int,
    top_level_allocation: Dict[str, int],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for party in parties:
        total_seats = top_level_allocation.get(party.party, 0)
        list_allocations = allocate_party_list_units(party, total_seats) if total_seats > 0 else {}
        list_rows: List[Dict[str, Any]] = []
        for unit in party.list_units:
            unit_total_seats = list_allocations.get(unit.list_id, 0)
            list_rows.append(
                {
                    "list_id": unit.list_id,
                    "label": unit.label,
                    "district_id": unit.district_id,
                    "district_name": unit.district_name,
                    "votes": unit.votes,
                    "vote_share_valid_percent": round(vote_share_percent(unit.votes, valid_votes), 4),
                    "vote_share_party_percent": round(vote_share_percent(unit.votes, party.total_votes), 4),
                    "direct_mandates": unit.direct_mandates,
                    "list_seats": max(0, unit_total_seats - unit.direct_mandates),
                    "total_seats": unit_total_seats,
                }
            )
        rows.append(
            {
                "party": party.party,
                "list_type": party.list_type,
                "votes": party.total_votes,
                "vote_share_valid_percent": round(vote_share_percent(party.total_votes, valid_votes), 4),
                "vote_share_qualifying_percent": round(vote_share_percent(party.total_votes, qualifying_vote_total), 4),
                "direct_mandates": party.total_direct_mandates,
                "list_seats": max(0, total_seats - party.total_direct_mandates),
                "total_seats": total_seats,
                "lists": list_rows,
            }
        )
    rows.sort(key=lambda row: (-int(row["total_seats"]), -int(row["votes"]), str(row["party"])))
    return rows


def calculate_rlp_seats(payload: Dict[str, Any]) -> Dict[str, Any]:
    parties = normalize_party_inputs(payload)
    _validate_direct_mandate_inputs(parties)

    explicit_valid_votes = payload.get("valid_list_votes")
    valid_votes = parse_int(explicit_valid_votes)
    if explicit_valid_votes is None:
        valid_votes = sum(party.total_votes for party in parties)
    base_seats = parse_int(payload.get("base_seats")) or DEFAULT_BASE_SEATS
    source_label = str(payload.get("source_label") or payload.get("source_url") or "").strip()

    if valid_votes <= 0:
        return {
            "status": "no_votes",
            "source_label": source_label,
            "valid_list_votes": valid_votes,
            "threshold_percent": 5.0,
            "threshold_votes_min": threshold_votes_min(valid_votes),
            "base_seats": base_seats,
            "total_seats": None,
            "balance_seats": None,
            "majority_bonus_party": None,
            "party_rows": build_party_rows(
                parties,
                valid_votes=valid_votes,
                qualifying_vote_total=0,
                top_level_allocation={},
            ),
            "notes": [
                "No positive Landesstimmen are available yet; seat allocation is undefined until results exist.",
            ],
        }

    qualifying_votes = {
        party.party: party.total_votes
        for party in parties
        if party.list_type != "none" and party.total_votes > 0 and Fraction(party.total_votes, valid_votes) >= THRESHOLD
    }

    unsupported_direct = _unsupported_direct_mandates(parties, qualifying_votes)
    if unsupported_direct:
        joined = ", ".join(unsupported_direct)
        raise ValueError(
            "Successful direct winners without a qualifying Landes- or Bezirksliste require "
            "bereinigte Landesstimmen that aggregate public inputs do not expose: "
            f"{joined}"
        )

    qualifying_parties = [party for party in parties if party.party in qualifying_votes]
    qualifying_vote_total = sum(qualifying_votes.values())

    for total_seats in range(base_seats, MAX_TOTAL_SEATS + 1):
        top_level_allocation, majority_bonus_party = apply_majority_rule(qualifying_votes, total_seats)
        balanced = True
        for party in qualifying_parties:
            party_seats = top_level_allocation.get(party.party, 0)
            if party_seats < party.total_direct_mandates:
                balanced = False
                break
            list_allocations = allocate_party_list_units(party, party_seats)
            if any(list_allocations.get(unit.list_id, 0) < unit.direct_mandates for unit in party.list_units):
                balanced = False
                break
        if not balanced:
            continue

        party_rows = build_party_rows(
            parties,
            valid_votes=valid_votes,
            qualifying_vote_total=qualifying_vote_total,
            top_level_allocation=top_level_allocation,
        )
        return {
            "status": "ok",
            "source_label": source_label,
            "valid_list_votes": valid_votes,
            "threshold_percent": 5.0,
            "threshold_votes_min": threshold_votes_min(valid_votes),
            "base_seats": base_seats,
            "total_seats": total_seats,
            "balance_seats": total_seats - base_seats,
            "majority_bonus_party": majority_bonus_party,
            "qualifying_vote_total": qualifying_vote_total,
            "qualifying_parties": sorted(qualifying_votes),
            "party_rows": party_rows,
            "allocation_by_party": dict(sorted(top_level_allocation.items())),
            "notes": [
                "Implements the RLP rules for threshold, majority safeguard, overhang balance, and optional Bezirkslisten.",
                "Uses the mathematically equivalent Sainte-Lague/Schepers highest-averages form and aborts on exact final-seat ties.",
            ],
        }

    raise RuntimeError(f"No balanced RLP seat allocation found up to {MAX_TOTAL_SEATS} total seats")


def example_input_payload() -> Dict[str, Any]:
    return {
        "source_label": "synthetic example",
        "base_seats": 101,
        "parties": [
            {
                "party": "Example Landesliste",
                "list_type": "land",
                "votes": 500000,
                "direct_mandates": 25,
            },
            {
                "party": "Example Bezirkslisten",
                "list_type": "district",
                "lists": [
                    {
                        "list_id": "bezirk-1",
                        "label": "Bezirk 1",
                        "district_id": "1",
                        "district_name": "Bezirk 1",
                        "votes": 120000,
                        "direct_mandates": 4,
                    },
                    {
                        "list_id": "bezirk-2",
                        "label": "Bezirk 2",
                        "district_id": "2",
                        "district_name": "Bezirk 2",
                        "votes": 90000,
                        "direct_mandates": 2,
                    },
                ],
            },
            {
                "party": "Small Party",
                "list_type": "land",
                "votes": 15000,
                "direct_mandates": 0,
            },
        ],
    }
