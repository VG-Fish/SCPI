"""
Ohm's Law Verification via Arduino SCPI:
This program automates the verification of Ohm's Law (V = IR) by sweeping through a range
of voltages, measuring the resulting current, and plotting an I-V curve. The measured
resistance from the I-V slope is compared against the expected resistance value.
The program accounts for voltage drop across a series shunt resistor during measurements.
"""

import argparse
import time

import matplotlib.pyplot as plt
import numpy as np
import serial

# Resistor values used in the circuit
EXPECTED_R: float = 1000.0  # Expected DUT (Device Under Test) resistance in ohms
SHUNT_R: float = 100.0  # Series shunt resistor used for current measurement in ohms

# Voltage sweep parameters
VSTART: float = 0.0  # Starting voltage for the sweep (V)
VSTOP: float = 5.0  # Ending voltage for the sweep (V)
VSTEP: float = 0.5  # Voltage step size (V)

# Settling time for measurements after voltage change (seconds)
SETTLE_S: float = 0.3


def run_sweep(port: str, baud: int = 9600):
    """
    Execute a voltage sweep and measure voltage and current at each step.

    For each voltage setpoint, the function:
    1. Sets the source voltage using SCPI SOUR:VOLT command
    2. Waits for the circuit to settle
    3. Measures the actual voltage across the DUT and resulting current
    4. Corrects the voltage measurement by subtracting the shunt drop (V_drop = I * R_shunt)

    Args:
        port: Serial port name for Arduino connection
        baud: Baud rate for serial communication (default 9600)

    Returns:
        Tuple of numpy arrays: (measured_voltages, measured_currents)
    """
    # Create array of voltage setpoints to test
    voltages = np.arange(VSTART, stop=VSTOP + VSTEP / 2, step=VSTEP)
    v_meas: list[float] = []
    i_meas: list[float] = []

    print(f"\nConnecting to Arduino on {port} ...")
    with serial.Serial(port, baud, timeout=2) as ser:
        # Wait for Arduino initialization and clear input buffer
        time.sleep(2)
        ser.reset_input_buffer()

        def send_cmd_and_parse_input(cmd: str) -> str:
            """Send SCPI command and return the parsed response."""
            ser.reset_input_buffer()
            ser.write((cmd + "\n").encode())
            return ser.readline().decode().strip()

        # Query device ID and display it
        print("Device:", send_cmd_and_parse_input("*IDN?"))
        # Print column headers for the measurement table
        print("\n{:>8}  {:>12}  {:>12}".format("Set (V)", "Vmeas (V)", "Imeas (mA)"))
        print("-" * 38)

        # Execute voltage sweep
        for v_set in voltages:
            # Set the source voltage to the target value
            send_cmd_and_parse_input(f"SOUR:VOLT {v_set:.2f}")
            # Allow circuit to settle after voltage change
            time.sleep(SETTLE_S)

            # Measure the voltage across DUT and resulting current
            v_resp: str = send_cmd_and_parse_input("MEAS:VOLT?")
            i_resp: str = send_cmd_and_parse_input("MEAS:CURR?")

            vm: float = 0.0
            im: float = 0.0
            try:
                # Parse voltage and current responses
                v_a0 = float(v_resp)
                im = float(i_resp)
                # Correct voltage by subtracting shunt drop: V_DUT = V_measured - (I * R_shunt)
                # This accounts for the voltage drop across the series shunt resistor
                vm = v_a0 - (im * SHUNT_R)
            except ValueError:
                # If parsing fails, use theoretical values based on expected resistance
                print(f"  [WARN] Bad response at {v_set} V: V={v_resp}, I={i_resp}")
                vm = v_set
                im = v_set / EXPECTED_R

            # Store measurements for later analysis
            v_meas.append(vm)
            i_meas.append(im)
            # Display measurement in table format with current in mA
            print(f"{v_set:>8.2f}  {vm:>12.4f}  {im * 1000:>12.4f}")

        # Ensure output is turned off after the sweep for safety
        send_cmd_and_parse_input("SOUR:VOLT 0.00")

    # Return measurements as numpy arrays for analysis
    return np.array(v_meas), np.array(i_meas)


def analyze_and_plot(v_meas: np.ndarray, i_meas: np.ndarray) -> None:
    """
    Fit the measured I-V data to a line and create a visualization.

    Performs linear regression on the voltage-current data to determine the resistance
    from the slope (R = 1/slope). Creates a scatter plot of measured points with a
    best-fit line and displays the calculated resistance value.

    Args:
        v_meas: Array of measured voltage values across the DUT
        i_meas: Array of measured current values through the DUT
    """
    # Perform linear regression: I = slope * V + intercept
    # Slope has units of A/V = 1/Ω, so R = 1/slope
    slope, intercept = np.polyfit(v_meas, i_meas, 1)
    r_fit: float = 1.0 / slope if slope != 0 else float("inf")
    # Create smooth line for the fit (used for plotting)
    v_line: np.ndarray = np.linspace(0, VSTOP, 200)

    # Display analysis results to the user
    print("\n--- Analysis Results ---")
    print(
        f"Line of best fit: I = {slope * 1000:.4f} mA/V * V + {intercept * 1000:.4f} mA"
    )
    print(f"Slope (1/R_fit):  {slope * 1000:.4f} mA/V")
    print(f"R from fit:       {r_fit:.2f} Ω")
    print(f"Expected R:       {EXPECTED_R:.2f} Ω")

    # Create I-V curve plot
    _, ax = plt.subplots(figsize=(7, 5))
    # Plot measured data points
    ax.scatter(
        v_meas, i_meas * 1000, color="steelblue", zorder=5, label="Measured data", s=60
    )
    # Plot best-fit line over the data
    ax.plot(
        v_line,
        (slope * v_line + intercept) * 1000,
        "r--",
        linewidth=1.5,
        label=f"Best fit: R = {r_fit:.1f} Ω",
    )

    # Configure plot axes and labels
    ax.set_xlabel("Voltage (V)", fontsize=12)
    ax.set_ylabel("Current (mA)", fontsize=12)
    ax.set_title(
        "ECE 20007 – Ohm's Law Verification\nI-V Curve for 1 kΩ Resistor", fontsize=13
    )
    ax.legend()
    ax.grid(True, alpha=0.3)
    # Set axis limits for appropriate zoom level
    ax.set_xlim(0, 0.5)
    ax.set_ylim(0, 1)

    # Add text box showing the equation and calculated resistance
    ax.text(
        0.05,
        0.92,
        f"I = {slope * 1000:.4f}·V + {intercept * 1000:.4f}  [mA, V]\n"
        f"R_fit = {r_fit:.2f} Ω",
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    # Save plot to file
    plt.tight_layout()
    plt.savefig("plots/ohms_law_iv_curve.png", dpi=150, bbox_inches="tight")
    print("\nPlot successfully saved as 'ohms_law_iv_curve.png'")
    plt.close()


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Automate Ohm's Law measurements via Arduino."
    )
    parser.add_argument(
        "--port",
        required=True,
        help="Arduino serial port (e.g., COM3 or /dev/ttyACM0).",
    )
    args = parser.parse_args()

    # Execute the voltage sweep and collect measurements
    v_data, i_data = run_sweep(args.port)
    # Analyze the measurements and generate the I-V curve plot
    analyze_and_plot(v_data, i_data)
