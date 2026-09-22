"""Runs the scheduled Renfrew-Yoker bridge closure scrape on the Raspberry Pi."""

import sys

from bridge_closures.cache_refresh import main

if __name__ == "__main__":
    sys.exit(main())
