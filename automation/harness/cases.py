# -*- coding: utf-8 -*-
"""测试用例定义。

每条用例由若干步骤组成，每一步：
  set     该步要改变的输入（未列出的保持上一步的值）
  expect  期望的输出及允许的超时（ms）
  hold_ms 该步至少保持的时长，用于观察稳态行为
"""

CASES = [
    {
        "id": "TC-01",
        "name": "上升启动",
        "steps": [
            {"set": {"up": True}, "expect": [("motor_up", True, 200)]},
        ],
    },
    {
        "id": "TC-02",
        "name": "上限位停止",
        "steps": [
            {"set": {"up": True}, "expect": [("motor_up", True, 200)]},
            {"set": {"limit_top": True}, "expect": [("motor_up", False, 150)]},
        ],
    },
    {
        "id": "TC-03",
        "name": "自锁保持（松开按钮）",
        "steps": [
            {"set": {"up": True}, "expect": [("motor_up", True, 200)]},
            {"set": {"up": False}, "hold_ms": 300, "expect": [("motor_up", True, 100)]},
        ],
    },
    {
        "id": "TC-04",
        "name": "上升下降互锁",
        "steps": [
            {"set": {"up": True, "down": True}, "hold_ms": 200,
             "expect": [("motor_up", False, 100), ("motor_down", False, 100)]},
        ],
    },
    {
        "id": "TC-05",
        "name": "防夹短脉冲不触发（200 ms < 300 ms）",
        "steps": [
            {"set": {"up": True}, "expect": [("motor_up", True, 200)]},
            {"set": {"pinch": True}, "hold_ms": 200, "expect": [("alarm", False, 100)]},
            {"set": {"pinch": False}, "hold_ms": 300, "expect": [("alarm", False, 100)]},
        ],
    },
    {
        "id": "TC-06",
        "name": "防夹确认触发（持续 > 300 ms）",
        "steps": [
            {"set": {"up": True}, "expect": [("motor_up", True, 200)]},
            {"set": {"pinch": True}, "expect": [("alarm", True, 600), ("motor_up", False, 600)]},
        ],
    },
    {
        "id": "TC-07",
        "name": "防夹后反向回弹",
        "steps": [
            {"set": {"up": True}, "expect": [("motor_up", True, 200)]},
            {"set": {"pinch": True}, "expect": [("alarm", True, 600)]},
            {"set": {"pinch": False}, "expect": [("motor_down", True, 200)]},
        ],
    },
    {
        "id": "TC-08",
        "name": "故障锁存（撤防夹后不可再上升）",
        "steps": [
            {"set": {"up": True}, "expect": [("motor_up", True, 200)]},
            {"set": {"pinch": True}, "expect": [("alarm", True, 600)]},
            {"set": {"pinch": False, "up": True}, "hold_ms": 400,
             "expect": [("motor_up", False, 100), ("alarm", True, 100)]},
        ],
    },
    {
        "id": "TC-09",
        "name": "复位清除故障",
        "steps": [
            {"set": {"up": True, "pinch": True}, "expect": [("alarm", True, 600)]},
            {"set": {"pinch": False, "reset": True}, "expect": [("alarm", False, 200)]},
            {"set": {"reset": False}, "hold_ms": 200, "expect": [("alarm", False, 100)]},
        ],
    },
    {
        "id": "TC-10",
        "name": "复位后可再次运行",
        "steps": [
            {"set": {"up": True, "pinch": True}, "expect": [("alarm", True, 600)]},
            {"set": {"pinch": False, "reset": True}, "expect": [("alarm", False, 200)]},
            {"set": {"reset": False, "up": True}, "hold_ms": 900,
             "expect": [("motor_up", True, 300)]},
        ],
    },
    {
        "id": "TC-11",
        "name": "下降启动",
        "steps": [
            {"set": {"down": True}, "expect": [("motor_down", True, 200)]},
        ],
    },
    {
        "id": "TC-12",
        "name": "下限位停止",
        "steps": [
            {"set": {"down": True}, "expect": [("motor_down", True, 200)]},
            {"set": {"limit_bottom": True}, "expect": [("motor_down", False, 150)]},
        ],
    },
]
