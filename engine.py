"""Real-time microphone pitch shifting with pyo.

Run ``python engine.py --help`` for the available options.
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

_wx_dll_directory = Path(sys.prefix) / "Lib" / "site-packages" / "wx"
_wx_dll_handle = None
if _wx_dll_directory.is_dir():
	_wx_dll_handle = os.add_dll_directory(str(_wx_dll_directory))

from pyo import (
	Harmonizer,
	Input,
	Mix,
	Server,
	pa_get_default_devices_from_host,
	pa_get_devices_infos,
	pa_list_devices,
)
from audio_routing import pyo_device_index, restore_system_audio, route_system_audio


DEFAULT_SEMITONE_SHIFT = -0.3176665363
DEFAULT_WINDOW_SIZE = 432 / 48000.0
LOG_PATH = Path(__file__).with_name("trutune.log")


def configure_logging(background: bool) -> None:
	if background:
		logging.basicConfig(
			filename=LOG_PATH,
			level=logging.INFO,
			format="%(asctime)s %(levelname)s %(message)s",
		)
	else:
		logging.basicConfig(level=logging.INFO, format="%(message)s")


def report(message: str) -> None:
	logging.info(message)
	if not _background_mode:
		print(message)


_background_mode = False


def create_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Shift live stereo audio down to 432 Hz.")
	parser.add_argument(
		"--input-device",
		type=int,
		help="PortAudio input device index. The system default is used when omitted.",
	)
	parser.add_argument(
		"--output-device",
		type=int,
		help="PortAudio output device index. The system default is used when omitted.",
	)
	parser.add_argument(
		"--shift",
		type=float,
		default=DEFAULT_SEMITONE_SHIFT,
		help="Pitch shift in semitones (default: %(default)s).",
	)
	parser.add_argument(
		"--window-size",
		type=float,
		default=DEFAULT_WINDOW_SIZE,
		help="Harmonizer window size in seconds (default: %(default)s).",
	)
	parser.add_argument(
		"--list-devices",
		action="store_true",
		help="List PortAudio devices and exit.",
	)
	parser.add_argument(
		"--no-gui",
		action="store_true",
		help="Run without the pyo control window; stop with Ctrl+C.",
	)
	parser.add_argument(
		"--background",
		action="store_true",
		help="Run silently without a GUI or console window.",
	)
	parser.add_argument(
		"--microphone",
		action="store_true",
		help="Use the physical microphone instead of automatic VB-CABLE system audio.",
	)
	parser.add_argument(
		"--poll-interval",
		type=float,
		default=2.0,
		help="Seconds between automatic device checks (default: %(default)s).",
	)
	parser.add_argument("--restore-audio", action="store_true", help=argparse.SUPPRESS)
	parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
	return parser


def default_device_indices() -> tuple[int, int]:
	"""Return the current Windows DirectSound input and output device IDs."""
	try:
		input_device, output_device = pa_get_default_devices_from_host("directsound")
		if input_device >= 0 and output_device >= 0:
			return input_device, output_device
	except RuntimeError:
		pass

	devices = pa_get_devices_infos()
	if isinstance(devices, tuple):
		input_devices, output_devices = devices
	else:
		input_devices = {
			index: info for index, info in devices.items() if "Input" in info["name"]
		}
		output_devices = {
			index: info for index, info in devices.items() if "Output" in info["name"]
		}
	if not input_devices or not output_devices:
		raise RuntimeError("No usable input and output devices were found")
	return next(iter(input_devices)), next(iter(output_devices))


def worker_args(args: argparse.Namespace, input_device: int, output_device: int) -> list[str]:
	command = [
		sys.executable,
		str(Path(__file__).resolve()),
		"--worker",
		"--input-device",
		str(input_device),
		"--output-device",
		str(output_device),
		"--shift",
		str(args.shift),
		"--window-size",
		str(args.window_size),
	]
	if args.no_gui or args.background:
		command.append("--no-gui")
	if args.background:
		command.append("--background")
	return command


def stop_worker(worker: subprocess.Popen[bytes]) -> None:
	if worker.poll() is not None:
		return
	worker.terminate()
	try:
		worker.wait(timeout=5)
	except subprocess.TimeoutExpired:
		worker.kill()
		worker.wait()


def run_worker(args: argparse.Namespace) -> None:
	server = Server(duplex=1)
	server.setInputDevice(args.input_device)
	server.setOutputDevice(args.output_device)

	server.boot()
	server.start()

	try:
		input_signal = Input(chnl=[0, 1])
		shifted_left = Harmonizer(
			input_signal[0], transpo=args.shift, winsize=args.window_size
		)
		shifted_right = Harmonizer(
			input_signal[1], transpo=args.shift, winsize=args.window_size
		)
		Mix([shifted_left, shifted_right], voices=2).out()

		report(f"TRUtune active: {args.shift:g} semitones")
		if args.no_gui:
			while True:
				time.sleep(1)
		else:
			server.gui(title="TRUtune")
	except KeyboardInterrupt:
		report("Stopping TRUtune.")
	finally:
		server.stop()
		server.shutdown()


def run_supervisor(args: argparse.Namespace) -> None:
	current_devices: tuple[int, int] | None = None
	worker: subprocess.Popen[bytes] | None = None
	automatic_input = args.input_device is None
	automatic_output = args.output_device is None
	route_active = False

	try:
		if not args.microphone and args.input_device is None:
			_, physical_output = default_device_indices()
			route_system_audio()
			args.input_device = pyo_device_index("CABLE Output (VB-Audio Virtual Cable)", True)
			args.output_device = physical_output
			automatic_input = False
			automatic_output = False
			route_active = True
			report("System audio routed through VB-CABLE.")

		while True:
			default_input, default_output = default_device_indices()
			input_device = default_input if automatic_input else args.input_device
			output_device = default_output if automatic_output else args.output_device
			selected_devices = (input_device, output_device)

			if worker is None or worker.poll() is not None or selected_devices != current_devices:
				if worker is not None:
					stop_worker(worker)
				popen_kwargs = {}
				if args.background and sys.platform == "win32":
					popen_kwargs = {
						"creationflags": subprocess.CREATE_NO_WINDOW,
						"stdin": subprocess.DEVNULL,
						"stdout": subprocess.DEVNULL,
						"stderr": subprocess.DEVNULL,
					}
				worker = subprocess.Popen(worker_args(args, input_device, output_device), **popen_kwargs)
				current_devices = selected_devices
				report(f"Using input device {input_device}, output device {output_device}")

			time.sleep(args.poll_interval)
	except KeyboardInterrupt:
		report("Stopping TRUtune.")
	finally:
		if worker is not None and worker.poll() is None:
			stop_worker(worker)
		if route_active:
			restore_system_audio()
			report("Restored the previous Windows playback device.")


def run(args: argparse.Namespace) -> None:
	global _background_mode
	_background_mode = args.background
	configure_logging(args.background)
	if args.list_devices:
		pa_list_devices()
		return
	if getattr(args, "restore_audio", False):
		restore_system_audio()
		return
	if args.window_size <= 0 or args.window_size > 1:
		raise ValueError("--window-size must be greater than 0 and no more than 1 second")
	if args.poll_interval <= 0:
		raise ValueError("--poll-interval must be greater than 0")
	if args.background:
		args.no_gui = True
	if args.worker:
		run_worker(args)
	else:
		run_supervisor(args)


def main() -> None:
	parser = create_parser()
	run(parser.parse_args())


if __name__ == "__main__":
	main()
