"""Convert a CSV file to a JSON array of objects."""

import argparse
import csv
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a CSV file to JSON.")
    parser.add_argument("path", help="the CSV file to read")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent")
    args = parser.parse_args()

    with open(args.path, newline="") as f:
        rows = list(csv.DictReader(f))
    json.dump(rows, sys.stdout, indent=args.indent)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
