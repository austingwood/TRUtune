"""Windows audio routing helpers for VB-CABLE."""

from __future__ import annotations

import ctypes
import json
from pathlib import Path
from typing import Any

from comtypes import COMMETHOD, CLSCTX_ALL, GUID, HRESULT, IUnknown, CoCreateInstance
from pycaw.pycaw import AudioUtilities


ROUTE_STATE_PATH = Path(__file__).with_name("trutune_audio_route.json")
CABLE_INPUT_NAME = "CABLE Input (VB-Audio Virtual Cable)"
CABLE_OUTPUT_NAME = "CABLE Output (VB-Audio Virtual Cable)"


class IPolicyConfig(IUnknown):
    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    _methods_ = [
        COMMETHOD([], HRESULT, "GetMixFormat"),
        COMMETHOD([], HRESULT, "GetDeviceFormat"),
        COMMETHOD([], HRESULT, "ResetDeviceFormat"),
        COMMETHOD([], HRESULT, "SetDeviceFormat"),
        COMMETHOD([], HRESULT, "GetProcessingPeriod"),
        COMMETHOD([], HRESULT, "SetProcessingPeriod"),
        COMMETHOD([], HRESULT, "GetShareMode"),
        COMMETHOD([], HRESULT, "SetShareMode"),
        COMMETHOD([], HRESULT, "GetPropertyValue"),
        COMMETHOD([], HRESULT, "SetPropertyValue"),
        COMMETHOD(
            [],
            HRESULT,
            "SetDefaultEndpoint",
            (['in'], ctypes.c_wchar_p, "device_id"),
            (['in'], ctypes.c_int, "role"),
        )
    ]


POLICY_CONFIG_CLSID = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")


def _devices() -> list[Any]:
    return AudioUtilities.GetAllDevices()


def _find_device(name: str) -> Any:
    for device in _devices():
        if device.FriendlyName.strip() == name:
            return device
    raise RuntimeError(f"Audio device not found: {name}")


def pyo_device_index(name: str, input_device: bool, host_api_index: int | None = None) -> int:
    from pyo import pa_get_devices_infos

    devices = pa_get_devices_infos()
    if isinstance(devices, tuple):
        devices = devices[0 if input_device else 1]
    for index, info in devices.items():
        if (
            info["name"].strip().startswith(name.split(" (", 1)[0])
            and (host_api_index is None or info["host api index"] == host_api_index)
        ):
            return index
    direction = "input" if input_device else "output"
    raise RuntimeError(f"Could not map VB-CABLE {direction} device to a pyo device")


def cable_input_for_output(output_device: int) -> int:
    from pyo import pa_get_devices_infos

    devices = pa_get_devices_infos()
    input_devices, output_devices = devices if isinstance(devices, tuple) else ({}, devices)
    output_info = output_devices.get(output_device)
    if output_info is None:
        raise RuntimeError(f"Output device {output_device} is no longer available")
    return pyo_device_index(
        CABLE_OUTPUT_NAME,
        input_device=True,
        host_api_index=output_info["host api index"],
    )


def set_default_endpoint(device_id: str) -> None:
    policy = CoCreateInstance(POLICY_CONFIG_CLSID, IPolicyConfig, CLSCTX_ALL)
    for role in (0, 1, 2):
        policy.SetDefaultEndpoint(device_id, role)


def _current_default_output_id() -> str:
    return AudioUtilities.GetSpeakers().id


def endpoint_id_for_pyo_output(output_device: int) -> str:
    from pyo import pa_get_devices_infos

    devices = pa_get_devices_infos()
    output_devices = devices[1] if isinstance(devices, tuple) else devices
    info = output_devices.get(output_device)
    if info is None:
        raise RuntimeError(f"Output device {output_device} is no longer available")
    name = info["name"].strip()
    for device in _devices():
        if device.FriendlyName.startswith(name) and "CABLE Input" not in device.FriendlyName:
            return device.id
    active_physical = [
        device
        for device in _devices()
        if "CABLE" not in device.FriendlyName
        and "Active" in str(getattr(device, "state", ""))
    ]
    if active_physical:
        return active_physical[0].id
    raise RuntimeError(f"Could not map pyo output device {output_device} to Windows audio")


def route_system_audio(previous_output_id: str | None = None) -> dict[str, str]:
    if ROUTE_STATE_PATH.exists():
        state = json.loads(ROUTE_STATE_PATH.read_text(encoding="utf-8"))
        if state.get("previous_output_id") and "CABLE Input" not in state["previous_output_id"]:
            set_default_endpoint(state["previous_output_id"])
        ROUTE_STATE_PATH.unlink(missing_ok=True)
    cable_input = _find_device(CABLE_INPUT_NAME)
    cable_output = _find_device(CABLE_OUTPUT_NAME)
    if previous_output_id is None:
        previous_output_id = _current_default_output_id()
    if "CABLE Input" in previous_output_id:
        raise RuntimeError("Windows is already routed to VB-CABLE; select a physical output first")
    set_default_endpoint(cable_input.id)
    state = {
        "previous_output_id": previous_output_id,
        "cable_input_id": cable_input.id,
        "cable_output_id": cable_output.id,
    }
    ROUTE_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def restore_system_audio() -> None:
    if not ROUTE_STATE_PATH.exists():
        return
    state = json.loads(ROUTE_STATE_PATH.read_text(encoding="utf-8"))
    set_default_endpoint(state["previous_output_id"])
    ROUTE_STATE_PATH.unlink(missing_ok=True)
