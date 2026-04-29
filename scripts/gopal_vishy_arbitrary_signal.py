"""
Arbitrary Signal XY Mode Display:
This program reads voltage measurements from Arduino pins A0 and A1 via SCPI protocol
and displays them in XY mode, where A0 is plotted on the X-axis and A1 is plotted on the Y-axis.
"""

import argparse
import time

import matplotlib.pyplot as plt
import numpy as np
import serial

# Serial communication configuration
BAUD_RATE: int = 115200

# Duration to sample voltage data (in seconds)
SAMPLING_DURATION: int = 3


def read_voltages(
    port: str, duration: int
) -> tuple[list[float], list[float]] | tuple[None, None]:
    """
    Read voltages from A0 and A1 using SCPI protocol.

    Sends MEAS:VOLT?A0,A1 commands via serial connection and parses the comma-separated
    voltage responses. Continues reading for the specified duration or returns early if
    an error occurs.

    Args:
        port: Serial port name (e.g., '/dev/cu.usbmodem14101' or 'COM3')
        duration: Sampling duration in seconds

    Returns:
        Tuple of two lists containing A0 and A1 voltage readings, or (None, None) if error
    """
    voltages_a0: list[float] = []
    voltages_a1: list[float] = []

    try:
        # Open serial connection with specified baud rate and timeout
        with serial.Serial(port, BAUD_RATE, timeout=2) as ser:
            # Wait for Arduino to initialize after serial connection
            time.sleep(2)
            # Clear any leftover data in the input buffer
            ser.reset_input_buffer()

            print(f"Reading for {duration} seconds...")
            start_time: float = time.time()

            # Continue reading until duration is reached
            while time.time() - start_time < duration:
                # Send SCPI command to measure voltages on pins A0 and A1
                ser.write(b"MEAS:VOLT?A0,A1\n")

                response: str = ser.readline().decode("utf-8").strip()
                # Only process valid responses (not error messages)
                if response and not response.startswith("ERR"):
                    try:
                        # Parse comma-separated voltage values
                        a0_voltage, a1_voltage = tuple(map(float, response.split(",")))
                        voltages_a0.append(a0_voltage)
                        voltages_a1.append(a1_voltage)
                    except ValueError:
                        # Skip responses that cannot be parsed as floats
                        continue

    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        return None, None

    return voltages_a0, voltages_a1


def plot_xy_mode(v_a0: list[float], v_a1: list[float]) -> None:
    """
    Plot voltages in XY mode.
    A0 on X-axis, A1 on Y-axis. This visualization reveals patterns and relationships
    between two simultaneous signals.

    Args:
        v_a0: List of voltage readings from pin A0 (X-axis)
        v_a1: List of voltage readings from pin A1 (Y-axis)
    """
    # Validate that we have data to plot
    if not v_a0 or not v_a1:
        print("No data to plot")
        return

    # Create square figure for equal aspect ratio visualization
    plt.figure(figsize=(8, 8))
    # Plot each (A0, A1) pair as a scatter point; small size and transparency reveal density
    plt.scatter(v_a0, v_a1, s=3, alpha=0.6, color="blue")

    # Configure axes labels and title
    plt.xlabel("A0 Voltage (V)", fontsize=12)
    plt.ylabel("A1 Voltage (V)", fontsize=12)
    plt.title("XY Mode - Oscilloscope Display", fontsize=14)
    # Add grid for easier reading
    plt.grid(True, alpha=0.3)
    # Set axis limits to 0-2.2V (Arduino typical range)
    plt.xlim(-0.2, 2.2)
    plt.ylim(-0.2, 2.2)
    # Equal aspect ratio ensures X and Y axes are proportional
    plt.axis("equal")

    # Save plot to file
    plt.tight_layout()
    plt.savefig("plots/xy_mode_plot.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    # Parse command-line arguments
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Read voltages from Arduino A0 and A1 and plot in XY mode"
    )
    parser.add_argument(
        "--port", help="Serial port (e.g., /dev/cu.usbmodem14101 or COM3)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=SAMPLING_DURATION,
        help=f"Sampling duration in seconds (default: {SAMPLING_DURATION})",
    )
    args: argparse.Namespace = parser.parse_args()

    # Start the data acquisition process
    print("Starting voltage acquisition...")
    a0_data: list[float] | None
    a1_data: list[float] | None
    a0_data, a1_data = read_voltages(args.port, args.duration)

    # Process and display results if data was successfully collected
    if a0_data and a1_data:
        print(f"Collected {len(a0_data)} samples")
        # Display statistical summary of A0 measurements
        print(
            f"A0 - Min: {min(a0_data):.2f}V, Max: {max(a0_data):.2f}V, Avg: {np.mean(a0_data):.2f}V"
        )
        # Display statistical summary of A1 measurements
        print(
            f"A1 - Min: {min(a1_data):.2f}V, Max: {max(a1_data):.2f}V, Avg: {np.mean(a1_data):.2f}V"
        )
        # Generate XY mode plot and save to file
        plot_xy_mode(a0_data, a1_data)
    else:
        # Notify user if data acquisition failed
        print("Failed to acquire data")
