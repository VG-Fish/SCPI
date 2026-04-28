import argparse
import time

import matplotlib.pyplot as plt
import numpy as np
import serial

BAUD_RATE: int = 115200
SAMPLING_DURATION: int = 3


def read_voltages(
    port: str, duration: int
) -> tuple[list[float], list[float]] | tuple[None, None]:
    """
    Read voltages from A0 and A1 using SCPI protocol.

    Sends MEAS:VOLT?A0,A1 commands and parses responses.
    """
    voltages_a0: list[float] = []
    voltages_a1: list[float] = []

    try:
        with serial.Serial(port, BAUD_RATE, timeout=2) as ser:
            time.sleep(2)
            ser.reset_input_buffer()

            print(f"Reading for {duration} seconds...")
            start_time: float = time.time()

            while time.time() - start_time < duration:
                ser.write(b"MEAS:VOLT?A0,A1\n")

                response: str = ser.readline().decode("utf-8").strip()
                if response and not response.startswith("ERR"):
                    try:
                        a0_voltage, a1_voltage = tuple(map(float, response.split(",")))
                        voltages_a0.append(a0_voltage)
                        voltages_a1.append(a1_voltage)
                    except ValueError:
                        continue

    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        return None, None

    return voltages_a0, voltages_a1


def plot_xy_mode(v_a0: list[float], v_a1: list[float]) -> None:
    """
    Plot voltages in XY mode (like oscilloscope XY display).
    A0 on X-axis, A1 on Y-axis.
    """
    if not v_a0 or not v_a1:
        print("No data to plot")
        return

    plt.figure(figsize=(8, 8))
    plt.scatter(v_a0, v_a1, s=3, alpha=0.6, color="blue")

    plt.xlabel("A0 Voltage (V)", fontsize=12)
    plt.ylabel("A1 Voltage (V)", fontsize=12)
    plt.title("XY Mode - Oscilloscope Display", fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.xlim(-0.2, 2.2)
    plt.ylim(-0.2, 2.2)
    plt.axis("equal")

    plt.tight_layout()
    plt.savefig("plots/xy_mode_plot.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Read voltages from Arduino A0 and A1 and plot in XY mode"
    )
    parser.add_argument(
        "--port", help="Serial port (e.g., /dev/cu.usbmodem14101 or COM3)"
    )
    parser.add_argument(
        "--duration", type=int, default=SAMPLING_DURATION, help=f"Sampling duration in seconds (default: {SAMPLING_DURATION})"
    )
    args: argparse.Namespace = parser.parse_args()

    print("Starting voltage acquisition...")
    a0_data: list[float] | None
    a1_data: list[float] | None
    a0_data, a1_data = read_voltages(args.port, args.duration)

    if a0_data and a1_data:
        print(f"Collected {len(a0_data)} samples")
        print(
            f"A0 - Min: {min(a0_data):.2f}V, Max: {max(a0_data):.2f}V, Avg: {np.mean(a0_data):.2f}V"
        )
        print(
            f"A1 - Min: {min(a1_data):.2f}V, Max: {max(a1_data):.2f}V, Avg: {np.mean(a1_data):.2f}V"
        )
        plot_xy_mode(a0_data, a1_data)
    else:
        print("Failed to acquire data")
