# -*- coding: utf-8 -*-
"""用例执行、断言与报告生成。"""
import datetime
import pathlib
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List

from .cases import CASES
from .client import PlcClient

POLL_MS = 20


@dataclass
class StepResult:
    index: int
    passed: bool
    elapsed_ms: float
    detail: str = ""


@dataclass
class CaseResult:
    case_id: str
    name: str
    passed: bool
    duration_ms: float
    steps: List[StepResult] = field(default_factory=list)


def _wait_for(plc: PlcClient, expects, timeout_ms: float) -> tuple:
    """轮询直到全部期望满足或超时。返回 (是否通过, 耗时 ms, 说明)"""
    start = time.monotonic()
    satisfied: Dict[str, float] = {}

    while True:
        elapsed = (time.monotonic() - start) * 1000
        outs = plc.read_outputs()

        for name, expected, limit in expects:
            if name in satisfied:
                continue
            if outs.get(name) == expected and elapsed <= limit:
                satisfied[name] = elapsed

        pending = [e for e in expects if e[0] not in satisfied]
        if not pending:
            return True, elapsed, ""

        if elapsed > timeout_ms:
            detail = "；".join(
                f"{e[0]} 期望 {e[1]}，实测 {outs.get(e[0])}" for e in pending)
            return False, elapsed, f"超时 {elapsed:.0f} ms（{detail}）"

        time.sleep(POLL_MS / 1000)


def _reset_device(plc: PlcClient) -> None:
    """每个用例执行前复位被测对象。

    不做这一步，上一个用例遗留的故障锁存会让后续用例全部失败——
    这是自动化测试里最典型的"用例间状态污染"。
    """
    idle = {k: False for k in
            ["up", "down", "limit_top", "limit_bottom", "pinch", "reset"]}
    plc.write_inputs(idle)
    time.sleep(0.05)
    plc.write_inputs({**idle, "reset": True})
    time.sleep(0.15)
    plc.write_inputs(idle)
    time.sleep(0.05)


def run_case(plc: PlcClient, case: dict) -> CaseResult:
    _reset_device(plc)
    start = time.monotonic()
    steps: List[StepResult] = []
    inputs = {k: False for k in
              ["up", "down", "limit_top", "limit_bottom", "pinch", "reset"]}

    for idx, step in enumerate(case["steps"], 1):
        inputs.update(step.get("set", {}))
        plc.write_inputs(inputs)

        expects = step.get("expect", [])
        hold_ms = step.get("hold_ms", 0)
        timeout = max([e[2] for e in expects] + [hold_ms, 100]) + 200

        step_start = time.monotonic()
        ok, elapsed, detail = _wait_for(plc, expects, timeout)

        # 保持时长：观察稳态
        if hold_ms:
            remain = hold_ms - (time.monotonic() - step_start) * 1000
            if remain > 0:
                time.sleep(remain / 1000)
                outs = plc.read_outputs()
                for name, expected, _ in expects:
                    if outs.get(name) != expected:
                        ok = False
                        detail = f"保持期断言失败：{name} 期望 {expected} 实测 {outs.get(name)}"

        steps.append(StepResult(idx, ok, elapsed, detail))
        if not ok:
            break

    return CaseResult(case["id"], case["name"], all(s.passed for s in steps),
                      (time.monotonic() - start) * 1000, steps)


def run_all(plc: PlcClient) -> List[CaseResult]:
    return [run_case(plc, c) for c in CASES]


def write_markdown(results: List[CaseResult], backend: str, out: pathlib.Path):
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    duration = sum(r.duration_ms for r in results) / 1000
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# 车窗控制自动化测试报告", "",
        f"- 执行时间：{ts}",
        f"- 执行后端：{backend}",
        f"- 用例总数：{total}",
        f"- 通过：{passed}　失败：{total - passed}",
        f"- 总耗时：{duration:.1f} s", "",
        "## 用例结果", "",
        "| 编号 | 用例 | 结果 | 耗时 |",
        "|---|---|---|---|",
    ]
    for r in results:
        mark = "通过" if r.passed else "**失败**"
        lines.append(f"| {r.case_id} | {r.name} | {mark} | {r.duration_ms/1000:.2f} s |")

    failures = [r for r in results if not r.passed]
    if failures:
        lines += ["", "## 失败详情", ""]
        for r in failures:
            lines.append(f"### {r.case_id} {r.name}")
            for s in r.steps:
                if not s.passed:
                    lines.append(f"- 步骤 {s.index}：{s.detail}")
            lines.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def write_junit(results: List[CaseResult], out: pathlib.Path):
    suite = ET.Element("testsuite", name="window-plc",
                       tests=str(len(results)),
                       failures=str(sum(1 for r in results if not r.passed)))
    for r in results:
        case = ET.SubElement(suite, "testcase", classname="WindowControl",
                             name=f"{r.case_id} {r.name}",
                             time=f"{r.duration_ms/1000:.3f}")
        if not r.passed:
            fail = ET.SubElement(case, "failure", message="断言失败")
            fail.text = "\n".join(s.detail for s in r.steps if not s.passed)
    out.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(out, encoding="utf-8", xml_declaration=True)
