#!/usr/bin/env python3
"""Generic CLI entry point for the election poller."""

from __future__ import annotations

import poll_election_core


def main() -> None:
    poll_election_core.main()


if __name__ == "__main__":
    main()
