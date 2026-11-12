# -*- coding: utf-8 -*-
"""PLC 客户端接口与两种后端实现。

同一套测试用例可以跑在：
  - SimPlc     本地模拟器（无需硬件，CI 可跑）
  - Snap7Plc   真实 S7-1200（或 S7-PLCSIM）

被测对象约定：
  输入：up, down, limit_top, limit_bottom, pinch, reset   -> I0.0 ~ I0.5
  输出：motor_up, motor_down, alarm                        -> Q0.0 ~ Q0.2
"""
import time
from typing import Dict, Protocol

INPUTS = ["up", "down", "limit_top", "limit_bottom", "pinch", "reset"]
OUTPUTS = ["motor_up", "motor_down", "alarm"]


class PlcClient(Protocol):
    def write_inputs(self, values: Dict[str, bool]) -> None: ...
    def read_outputs(self) -> Dict[str, bool]: ...
    def close(self) -> None: ...


# --------------------------------------------------------------------------
# 模拟器：与 v3 梯形图逻辑保持一致，按 10 ms 步长推进
# --------------------------------------------------------------------------
class SimPlc:
    SCAN_MS = 10

    def __init__(self):
        self.inp = {k: False for k in INPUTS}
        self.fault = False
        self.confirm_ms = 0
        self.retract_ms = 0
        self.motor_up = False
        self.motor_down = False
        self._last = time.monotonic()
        self._time = 0.0

    def write_inputs(self, values: Dict[str, bool]) -> None:
        self._advance()
        self.inp.update(values)

    def read_outputs(self) -> Dict[str, bool]:
        self._advance()
        return {"motor_up": self.motor_up, "motor_down": self.motor_down, "alarm": self.fault}

    def close(self) -> None:
        pass

    def _advance(self):
        now = time.monotonic()
        dt_ms = (now - self._last) * 1000
        self._last = now
        while dt_ms >= self.SCAN_MS:
            self._step()
            dt_ms -= self.SCAN_MS

    def _step(self) -> None:
        i = self.inp

        # 段1：防夹确认（300 ms，仅运行中采信）
        if i["pinch"] and (self.motor_up or self.motor_down):
            self.confirm_ms += self.SCAN_MS
        else:
            self.confirm_ms = 0

        # 段2：故障置位
        if self.confirm_ms >= 300 and not self.fault:
            self.fault = True
            self.retract_ms = 0

        # 段3：回弹计时
        if self.fault and self.retract_ms < 800:
            self.retract_ms += self.SCAN_MS

        # 段7：故障复位
        if i["reset"]:
            self.fault = False
            self.confirm_ms = 0
            self.retract_ms = 0

        # 段4：上升
        up_cmd = (i["up"] or self.motor_up) and not i["down"] and not i["limit_top"] and not self.fault
        # 段5：下降（含回弹支路）
        down_cmd = ((i["down"] or self.motor_down) and not i["up"] and not i["limit_bottom"] and not self.fault) \
            or (self.fault and self.retract_ms < 800)

        self.motor_up = bool(up_cmd)
        self.motor_down = bool(down_cmd)


# --------------------------------------------------------------------------
# 真实 PLC：通过 S7 协议读写 I / Q 区
# --------------------------------------------------------------------------
class Snap7Plc:
    """需要：
      1. pip install python-snap7
      2. CPU 属性中勾选「允许来自远程伙伴的 PUT/GET 通信访问」
      3. 与 PLC 处于同一网段（PLCSIM 用虚拟网卡）
    注意：真实硬件上 I 区会被扫描刷新，建议改为读写 M 区镜像。
    """

    def __init__(self, ip: str, rack: int = 0, slot: int = 1):
        import snap7

        self._snap7 = snap7
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot)
        if not self.client.get_connected():
            raise RuntimeError(f"连接失败：{ip}")

    def write_inputs(self, values: Dict[str, bool]) -> None:
        from snap7.util import set_bool

        data = bytearray(1)
        for idx, name in enumerate(INPUTS):
            if name in values:
                set_bool(data, 0, idx, bool(values[name]))
        self.client.write_area(self._snap7.type.Areas.PE, 0, 0, data)

    def read_outputs(self) -> Dict[str, bool]:
        from snap7.util import get_bool

        data = self.client.read_area(self._snap7.type.Areas.PA, 0, 0, 1)
        return {name: get_bool(data, 0, idx) for idx, name in enumerate(OUTPUTS)}

    def close(self) -> None:
        self.client.disconnect()
