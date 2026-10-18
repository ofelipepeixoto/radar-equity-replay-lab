from __future__ import annotations

import argparse
import json
import sys

from .core import InvalidInput, analyze
from .io import read_input, write_report


class _SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        self.exit(2, "Arguments rejected. Use --help for the local synthetic replay syntax.\n")


def main(argv=None):
    parser = _SafeParser(description="Replay local synthetic prices; no financial execution.")
    parser.add_argument("input")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args(argv)
    try:
        report = analyze(read_input(arguments.input))
        write_report(arguments.output, (json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except InvalidInput:
        print("Input or output rejected. Use the documented synthetic contract and a new output file.", file=sys.stderr)
        return 2
    print("Synthetic report created; human review is pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
