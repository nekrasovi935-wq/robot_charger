import pytest
from docking_logic import DockingLogic, State


def test_logic_init():
    logic = DockingLogic()
    assert logic.state == State.SEARCHING


def test_logic_lost_target():
    logic = DockingLogic()
    state, v, w = logic.step(None, now=10.0)
    assert state == State.SEARCHING
    assert v == 0.0
    assert w != 0.0
