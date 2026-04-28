import argparse
import time

import matplotlib.pyplot as plt
import numpy as np
import serial

EXPECTED_R: float = 1000.0
SHUNT_R: float = 100.0
VSTART: float = 0.0
VSTOP: float = 5.0
VSTEP: float = 0.5
SETTLE_S: float = 0.3


def run_sweep(port: str, baud: int = 9600):
    voltages = np.arange(VSTART, stop=VSTOP + VSTEP / 2, step=VSTEP)
    v_meas: list[float] = []
    i_meas: list[float] = []

    print(f"\nConnecting to Arduino on {port} ...")
    with serial.Serial(port, baud, timeout=2) as ser:
        time.sleep(2)
        ser.reset_input_buffer()

        def send_cmd_and_parse_input(cmd: str) -> str:
            ser.reset_input_buffer()
            ser.write((cmd + "\n").encode())
            return ser.readline().decode().strip()

        print("Device:", send_cmd_and_parse_input("*IDN?"))
        print("\n{:>8}  {:>12}  {:>12}".format("Set (V)", "Vmeas (V)", "Imeas (mA)"))
        print("-" * 38)

        for v_set in voltages:
            send_cmd_and_parse_input(f"SOUR:VOLT {v_set:.2f}")
            time.sleep(SETTLE_S)

            v_resp: str = send_cmd_and_parse_input("MEAS:VOLT?")
            i_resp: str = send_cmd_and_parse_input("MEAS:CURR?")

            vm: float = 0.0
            im: float = 0.0
            try:
                v_a0 = float(v_resp)
                im = float(i_resp)
                # Calculate voltage across the DUT only (subtracting shunt drop)
                vm = v_a0 - (im * SHUNT_R)
            except ValueError:
                print(f"  [WARN] Bad response at {v_set} V: V={v_resp}, I={i_resp}")
                vm = v_set
                im = v_set / EXPECTED_R

            v_meas.append(vm)
            i_meas.append(im)
            print(f"{v_set:>8.2f}  {vm:>12.4f}  {im * 1000:>12.4f}")

        # Ensure output is turned off after the sweep
        send_cmd_and_parse_input("SOUR:VOLT 0.00")

    return np.array(v_meas), np.array(i_meas)


def analyze_and_plot(v_meas: np.ndarray, i_meas: np.ndarray) -> None:
    slope, intercept = np.polyfit(v_meas, i_meas, 1)
    r_fit: float = 1.0 / slope if slope != 0 else float("inf")
    v_line: np.ndarray = np.linspace(0, VSTOP, 200)

    print("\n--- Analysis Results ---")
    print(
        f"Line of best fit: I = {slope * 1000:.4f} mA/V * V + {intercept * 1000:.4f} mA"
    )
    print(f"Slope (1/R_fit):  {slope * 1000:.4f} mA/V")
    print(f"R from fit:       {r_fit:.2f} Ω")
    print(f"Expected R:       {EXPECTED_R:.2f} Ω")

    _, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(
        v_meas, i_meas * 1000, color="steelblue", zorder=5, label="Measured data", s=60
    )
    ax.plot(
        v_line,
        (slope * v_line + intercept) * 1000,
        "r--",
        linewidth=1.5,
        label=f"Best fit: R = {r_fit:.1f} Ω",
    )

    ax.set_xlabel("Voltage (V)", fontsize=12)
    ax.set_ylabel("Current (mA)", fontsize=12)
    ax.set_title(
        "ECE 20007 – Ohm's Law Verification\nI-V Curve for 1 kΩ Resistor", fontsize=13
    )
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 0.5)
    ax.set_ylim(0, 1)

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

    plt.tight_layout()
    plt.savefig("ohms_law_iv_curve.png", dpi=150, bbox_inches="tight")
    print("\nPlot successfully saved as 'ohms_law_iv_curve.png'")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automate Ohm's Law measurements via Arduino."
    )
    parser.add_argument(
        "--port",
        required=True,
        help="Arduino serial port (e.g., COM3 or /dev/ttyACM0).",
    )
    args = parser.parse_args()

    v_data, i_data = run_sweep(args.port)
    analyze_and_plot(v_data, i_data)
