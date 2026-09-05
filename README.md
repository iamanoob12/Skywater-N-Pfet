# SkyWater N-PFET Device Characterization & Circuit Analysis

Educational exploration of N-channel and P-channel FET devices using the SkyWater 130nm PDK, ngspice simulations, and Python data analysis.

## Overview

This project demonstrates:
- **Device characterization**: DC and AC analysis of N/PMOS transistors
- **Circuit design**: Small-signal amplifier topologies (cascode, cascoded mirrors)
- **Data analysis**: Post-processing simulation results with Python to extract device parameters and frequency response

## Technology Stack

### SkyWater PDK
[SkyWater 130nm](https://skywater-pdk.readthedocs.io/) is an open-source Process Design Kit providing:
- NMOS and PMOS device models (`sky130_fd_pr__nfet_01v8`, `sky130_fd_pr__pfet_01v8`)
- Standard cell libraries
- Design rules and layouts

Installed at: `/usr/local/share/pdk`

### Ngspice
[Ngspice](http://ngspice.sourceforge.net/) is an open-source SPICE simulator for:
- DC operating point analysis (transistor biasing, I-V curves)
- AC small-signal analysis (gain, phase, frequency response)
- Transient analysis (time-domain behavior)

### Python
Post-processing scripts extract and visualize:
- DC device parameters ($g_m$, $r_o$, $V_{TH}$)
- Frequency response (poles, zeros, bandwidth)
- Circuit metrics (gain, output resistance, stability)

## Project Structure

```
Skywater-N-Pfet/
├── README.md (this file)
├── ParasticFet/          # Parasitic device effects
│   └── parastic.spice
├── SimpleCascode/        # Four-transistor telescopic cascode amplifier
│   ├── cascode.spice     # DC operating point
│   ├── ac_cascode.spice  # AC analysis
│   ├── Rout/             # Output resistance extraction
│   └── PolesZeros/       # Pole/zero analysis (Python)
└── SPICE/                # Detailed device characterization
    ├── Nmos/
    │   ├── Default_r0/   # IV curves at Vds=400mV
    │   └── gm/           # Transconductance extraction
    └── Pmos/
        ├── Default_r0/   # IV curves
        └── gm/           # Transconductance extraction
```

## Quick Start

### Prerequisites
```bash
# Install ngspice (Ubuntu/Debian)
sudo apt-get install ngspice

# Install Python dependencies
pip install numpy matplotlib scipy
```

### Running Simulations

Navigate to the desired simulation directory:

```bash
# DC operating point
ngspice -b cascode.spice -o op.log

# AC frequency response
ngspice ac_cascode.spice

# Device characterization
ngspice -b nmos_dc_iv.spice -o nmos.log
```

### Analyzing Results

```bash
# Extract poles and zeros from AC response
python PolesZeros/main.py

# Plot device characteristics
python SPICE/Nmos/Default_r0/fix_plot.py
```

## Key Concepts

### Device Parameters
Each transistor is characterized by:
- **$g_m$** (transconductance): small-signal gain
- **$r_o$** (output resistance): 1/$g_{ds}$
- **$V_{TH}$** (threshold voltage): turn-on voltage
- **$C_{gs}$, $C_{gd}$, $C_{sb}$**: parasitic capacitances

### Small-Signal Analysis and Frequency Respond
See more in SimpleCascode

## Examples

### SimpleCascode Amplifier
A four-transistor telescopic cascode:
- **Supply**: 1.6 V
- **Bias current**: 2 mA
- **Predicted gain**: ~29 dB
- **Measured gain**: ~30 dB
- **Dominant pole**: ~746 MHz

See [SimpleCascode/README.md](SimpleCascode/README.md) for detailed analysis.

## Simulation Workflow

1. **Design**: Set transistor sizes and biasing
2. **Simulate**: Run ngspice DC and AC analyses
3. **Extract**: Parse `.log` or `.csv` output files
4. **Analyze**: Compute device parameters and frequency response with Python
5. **Compare**: Validate hand calculations against simulation

## References

- [SkyWater PDK Documentation](https://skywater-pdk.readthedocs.io/)
- [Ngspice Manual](http://ngspice.sourceforge.net/docs.html)

## Notes

- All simulations assume SkyWater PDK installed at `/usr/local/share/pdk`
- Results are for **educational purposes** — validate designs against foundry models for production
- Circuit topologies demonstrate fundamental concepts in analog IC design 
