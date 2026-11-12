# -*- coding: utf-8 -*-
"""入口：选择后端，执行全部用例，输出报告。

用法：
  python run.py                    # 本地模拟器
  python run.py --backend plc --ip 192.168.0.1
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from harness.client import SimPlc, Snap7Plc
from harness.runner import run_all, write_junit, write_markdown

ROOT = pathlib.Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["sim", "plc"], default="sim")
    parser.add_argument("--ip", default="192.168.0.1")
    parser.add_argument("--rack", type=int, default=0)
    parser.add_argument("--slot", type=int, default=1)
    args = parser.parse_args()

    if args.backend == "sim":
        plc, label = SimPlc(), "本地模拟器（SimPlc）"
    else:
        plc, label = Snap7Plc(args.ip, args.rack, args.slot), f"S7-1200 {args.ip}"

    try:
        results = run_all(plc)
    finally:
        plc.close()

    write_markdown(results, label, REPORTS / "report.md")
    write_junit(results, REPORTS / "junit.xml")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print(f"后端：{label}")
    print(f"用例：{total}　通过：{passed}　失败：{total - passed}")
    for r in results:
        if not r.passed:
            print(f"  [FAIL] {r.case_id} {r.name}")
            for s in r.steps:
                if not s.passed:
                    print(f"         步骤 {s.index}: {s.detail}")
    print(f"报告：{REPORTS / 'report.md'}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
