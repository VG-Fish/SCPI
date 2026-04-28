import argparse
import time
from typing import cast

import matplotlib.pyplot as plt
import numpy as np
import serial

R_T = 10000.0
R_D = 5600.0
R_L = 56000.0


def calculate_rms(samples: np.ndarray) -> float:
    return np.sqrt(np.mean(np.square(samples)))


def run_capture(
    port: str, baud: int = 115200, duration: float = 3.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    pins = "A0,A1,A3"

    try:
        with serial.Serial(port, baud, timeout=1) as ser:
            time.sleep(2)
            ser.reset_input_buffer()

            timestamps, v_trans, v_data, v_out = [], [], [], []
            start_time: float = time.time()

            while (time.time() - start_time) < duration:
                ser.write(f"MEAS:VOLT? {pins}\n".encode())
                line: str = ser.readline().decode().strip()

                try:
                    vals: list[float] = [float(v) for v in line.split(",")]
                    if len(vals) == 3:
                        timestamps.append(time.time() - start_time)
                        v_trans.append(vals[0])
                        v_data.append(vals[1])
                        v_out.append(vals[2])
                except (ValueError, IndexError):
                    continue

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
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", required=True, help="Serial port (e.g. COM3 or /dev/ttyACM0)"
    )
    args: argparse.Namespace = parser.parse_args()

    captured_data: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = (
        run_capture(args.port)
    )
    if captured_data is None:
        return
    t, vt, vd, vo = captured_data

    vt_rms: float = calculate_rms(vt)
    vd_rms: float = calculate_rms(vd)
    vo_rms: float = calculate_rms(vo)

    # Power delivered to the load: P = V^2 / R
    p_out: float = (vo_rms**2) / R_L
    p_in: float = (vt_rms**2) / R_T
    efficiency: float = (p_out / p_in) * 100 if p_in > 0 else 0

    print(f"\n--- Measurement Results ({len(t)} samples) ---")
    print(f"V_trans RMS: {vt_rms:.4f} V")
    print(f"V_data  RMS: {vd_rms:.4f} V")
    print(f"V_out   RMS: {vo_rms:.4f} V")
    print(f"Power Out:   {p_out * 1e6:.4f} µW")
    print(f"Efficiency:  {efficiency:.2f}%")

    plt.style.use("seaborn-v0_8-muted")
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(t, vt, label="Transmitter ($V_{trans}$)", alpha=0.6, linestyle="--")
    ax.plot(t, vd, label="Data ($V_{data}$)", alpha=0.6, linestyle=":")
    ax.plot(
        t, vo, label="Superimposed Output ($V_{out}$)", color="black", linewidth=1.8
    )

    ax.set_title(
        f"Voltage Superposition Analysis\nP_load = {p_out * 1e6:.2f} μW | η = {efficiency:.1f}%"
    )
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Voltage (V)")
    ax.legend(frameon=True, loc="best")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("superposition_analysis.png", dpi=200)
    print("\nGraph saved as 'superposition_analysis.png'")


if __name__ == "__main__":
    main()
