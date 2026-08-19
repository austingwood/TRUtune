"""Visible device selector for starting TRUtune."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_wx_dll_directory = Path(sys.prefix) / "Lib" / "site-packages" / "wx"
if _wx_dll_directory.is_dir():
    os.add_dll_directory(str(_wx_dll_directory))

import wx
from pyo import pa_get_devices_infos


PROJECT_ROOT = Path(__file__).resolve().parent
ENGINE_PATH = PROJECT_ROOT / "engine.py"
CABLE_INPUT_PREFIX = "CABLE Output (VB-Audio Virtual Cable)"


def device_groups() -> tuple[dict[int, dict], dict[int, dict]]:
    devices = pa_get_devices_infos()
    if isinstance(devices, tuple):
        return devices
    inputs = {index: info for index, info in devices.items() if "Input" in info["name"]}
    outputs = {index: info for index, info in devices.items() if "Output" in info["name"]}
    return inputs, outputs


def label(index: int, info: dict) -> str:
    return f"[{index}] {info['name'].strip()} (host {info['host api index']})"


class SelectorFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title="TRUtune audio devices", size=(620, 220))
        inputs, outputs = device_groups()
        try:
            import engine

            _, default_output = engine.default_device_indices()
        except (RuntimeError, StopIteration):
            default_output = next(iter(outputs), None)

        output_host = outputs[default_output]["host api index"] if default_output in outputs else None
        compatible_inputs = {
            index: info
            for index, info in inputs.items()
            if output_host is None or info["host api index"] == output_host
        }
        default_input = next(
            (
                index
                for index, info in compatible_inputs.items()
                if info["name"].strip().startswith(CABLE_INPUT_PREFIX.split(" (", 1)[0])
            ),
            next(iter(compatible_inputs), None),
        )

        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 10, 10)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(panel, label="Input source:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.input_choice = wx.ComboBox(panel, style=wx.CB_READONLY)
        self.input_ids = list(compatible_inputs)
        for index in self.input_ids:
            self.input_choice.Append(label(index, compatible_inputs[index]))
        if default_input in self.input_ids:
            self.input_choice.SetSelection(self.input_ids.index(default_input))
        grid.Add(self.input_choice, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="Output destination:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.output_choice = wx.ComboBox(panel, style=wx.CB_READONLY)
        self.output_ids = list(outputs)
        for index in self.output_ids:
            self.output_choice.Append(label(index, outputs[index]))
        if default_output in self.output_ids:
            self.output_choice.SetSelection(self.output_ids.index(default_output))
        self.output_choice.Bind(wx.EVT_COMBOBOX, self.output_changed)
        grid.Add(self.output_choice, 1, wx.EXPAND)

        layout.Add(grid, 1, wx.ALL | wx.EXPAND, 18)
        start = wx.Button(panel, label="Start TRUtune")
        start.Bind(wx.EVT_BUTTON, self.start_trutune)
        layout.Add(start, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT, 18)
        panel.SetSizer(layout)
        self.Centre()

    def output_changed(self, event: wx.CommandEvent) -> None:
        inputs, outputs = device_groups()
        output_index = self.output_ids[self.output_choice.GetSelection()]
        output_host = outputs[output_index]["host api index"]
        compatible_inputs = {
            index: info for index, info in inputs.items() if info["host api index"] == output_host
        }
        self.input_choice.Clear()
        self.input_ids = list(compatible_inputs)
        for index in self.input_ids:
            self.input_choice.Append(label(index, compatible_inputs[index]))
        cable_index = next(
            (
                index
                for index, info in compatible_inputs.items()
                if info["name"].strip().startswith(CABLE_INPUT_PREFIX.split(" (", 1)[0])
            ),
            next(iter(compatible_inputs), None),
        )
        if cable_index in self.input_ids:
            self.input_choice.SetSelection(self.input_ids.index(cable_index))
        event.Skip()

    def start_trutune(self, event: wx.CommandEvent) -> None:
        input_selection = self.input_choice.GetSelection()
        output_selection = self.output_choice.GetSelection()
        if input_selection == wx.NOT_FOUND or output_selection == wx.NOT_FOUND:
            wx.MessageBox("Select an input and output device first.", "TRUtune", wx.OK | wx.ICON_WARNING)
            return

        command = [
            str(Path(sys.prefix) / "Scripts" / "pythonw.exe"),
            str(ENGINE_PATH),
            "--input-device",
            str(self.input_ids[input_selection]),
            "--output-device",
            str(self.output_ids[output_selection]),
        ]
        subprocess.Popen(command, cwd=PROJECT_ROOT)
        self.Close()


def main() -> None:
    app = wx.App(False)
    SelectorFrame().Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
