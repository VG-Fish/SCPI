"""
Voltage Superposition Analysis:
This program measures the superposition of two input signals (transmitter and data signals)
to verify the superposition principle in linear circuits. It measures three voltages:
- V_trans: Transmitter signal
- V_data: Data signal
- V_out: Combined output (should approximate V_trans + V_data)

The program calculates RMS values, power delivered to the load, and circuit efficiency,
then creates a time-domain plot showing all three signals.
"""

import argparse
import time
from typing import cast

import matplotlib.pyplot as plt
import numpy as np
import serial

# Resistor values used in the circuit for power calculations
R_T = 10000.0  # Transmitter circuit resistance in ohms
R_D = 5600.0  # Data circuit resistance in ohms
R_L = 56000.0  # Load resistance in ohms


def calculate_rms(samples: np.ndarray) -> float:
    """
    Calculate the RMS (Root Mean Square) value of a signal.

    RMS value is the square root of the mean of the squared samples. This is a measure
    of the effective (power-equivalent) value of a varying signal.

    Args:
        samples: Numpy array of signal samples

    Returns:
        RMS value of the signal
    """
    return np.sqrt(np.mean(np.square(samples)))


def run_capture(
    port: str, baud: int = 115200, duration: float = 3.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    """
    Capture voltage measurements from three pins for superposition analysis.

    Measures three signals over time:
    - A0: Transmitter signal (V_trans)
    - A1: Data signal (V_data)
    - A3: Combined output signal (V_out, which should approximate V_trans + V_data)

    Args:
        port: Serial port name for Arduino connection
        baud: Baud rate for serial communication (default 115200)
        duration: Measurement duration in seconds (default 3.0)

    Returns:
        Tuple of four numpy arrays: (timestamps, v_trans, v_data, v_out)
        Returns None if a serial error occurs
    """
    # Define which Arduino pins to measure
    pins = "A0,A1,A3"

    try:
        # Open serial connection to Arduino
        with serial.Serial(port, baud, timeout=1) as ser:
            # Wait for Arduino initialization and clear buffer
            time.sleep(2)
            ser.reset_input_buffer()

            # Initialize lists to store measurements
            timestamps, v_trans, v_data, v_out = [], [], [], []
            start_time: float = time.time()

            # Continue capturing data until duration is reached
            while (time.time() - start_time) < duration:
                # Send SCPI command to measure all three pins
                ser.write(f"MEAS:VOLT? {pins}\n".encode())
                # Read and decode the response
                line: str = ser.readline().decode().strip()

                try:
                    # Parse comma-separated voltage values
                    vals: list[float] = [float(v) for v in line.split(",")]
                    # Only store if we received exactly 3 voltage values
                    if len(vals) == 3:
                        # Record timestamp relative to capture start
                        timestamps.append(time.time() - start_time)
                        # Store individual voltage measurements
                        v_trans.append(vals[0])
                        v_data.append(vals[1])
                        v_out.append(vals[2])
                except (ValueError, IndexError):
                    # Skip responses that cannot be parsed
                    continue

            # Convert lists to numpy arrays and return
            return cast(
                tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
                (
                    np.array(timestamps),
                    np.array(v_trans),
                    np.array(v_data),
                    np.array(v_out),
                ),
            )

    except serial.SerialException as e:
        print(f"Serial Error: {e}")
        return None


def main():
    """
    Main program execution function.

    Orchestrates the data capture, analysis, and visualization of voltage superposition.
    Parses command-line arguments, captures voltage data, calculates RMS values and power
    metrics, and generates a plot.
    """
    # Parse command-line arguments
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", required=True, help="Serial port (e.g. COM3 or /dev/ttyACM0)"
    )
    args: argparse.Namespace = parser.parse_args()

    # Capture voltage data from Arduino
    captured_data: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = (
        run_capture(args.port)
    )
    # Exit early if data capture failed
    if captured_data is None:
        return
    # Unpack captured data into individual signal arrays
    t, vt, vd, vo = captured_data

    # Calculate RMS values for each signal
    vt_rms: float = calculate_rms(vt)
    vd_rms: float = calculate_rms(vd)
    vo_rms: float = calculate_rms(vo)

    # Calculate power delivered to the load using P = V^2 / R
    p_out: float = (vo_rms**2) / R_L
    # Calculate input power from transmitter signal
    p_in: float = (vt_rms**2) / R_T
    # Calculate circuit efficiency as output/input power percentage
    efficiency: float = (p_out / p_in) * 100 if p_in > 0 else 0

    # Display measurement statistics to the user
    print(f"\n--- Measurement Results ({len(t)} samples) ---")
    print(f"V_trans RMS: {vt_rms:.4f} V")
    print(f"V_data  RMS: {vd_rms:.4f} V")
    print(f"V_out   RMS: {vo_rms:.4f} V")
    print(f"Power Out:   {p_out * 1e6:.4f} µW")
    print(f"Efficiency:  {efficiency:.2f}%")

    # Create time-domain plot of all three signals
    plt.style.use("seaborn-v0_8-muted")
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot transmitter signal (dashed line)
    ax.plot(t, vt, label="Transmitter ($V_{trans}$)", alpha=0.6, linestyle="--")
    # Plot data signal (dotted line)
    ax.plot(t, vd, label="Data ($V_{data}$)", alpha=0.6, linestyle=":")
    # Plot combined output signal (solid black line)
    ax.plot(
        t, vo, label="Superimposed Output ($V_{out}$)", color="black", linewidth=1.8
    )

    # Configure plot title with power and efficiency metrics
    ax.set_title(
        f"Voltage Superposition Analysis\nP_load = {p_out * 1e6:.2f} μW | η = {efficiency:.1f}%"
    )
    # Configure axes labels
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Voltage (V)")
    # Add legend and grid for readability
    ax.legend(frameon=True, loc="best")
    ax.grid(True, alpha=0.3)

    # Save plot to file
    plt.tight_layout()
    plt.savefig("plots/superposition_analysis.png", dpi=200)
    print("\nGraph saved as 'superposition_analysis.png'")


if __name__ == "__main__":
    # Execute main program when script is run directly
    main()
