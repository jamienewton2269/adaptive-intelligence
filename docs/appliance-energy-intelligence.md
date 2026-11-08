# Appliance Energy Intelligence — design and acceptance gate

Developed by JNSystems. In loving memory of Becki and Dad.

## Purpose

Reduce environmental impact **and grid electricity consumption**, while meeting
the household's comfort and appliance-completion requirements. This is a
module of Adaptive Intelligence, not another HA installation.

## Inputs on HA-General (observed November 2026)

- `sensor.0x449fdafffec0aeb3_power` and its energy/current/voltage companions:
  **unknown**; source must be repaired and verified before fingerprint learning.
- `sensor.pj2101a_1p_wifi_smart_meter_power`: house meter, available. Its
  import/export direction, solar generation, sampling frequency and resets
  must be confirmed before using in carbon arithmetic.
- Dedicated NAS smart-plug meters are also available; these are not washing
  machine / dishwasher meters and should not be relabelled.

## Fingerprinting

1. Ingest timestamped power data; check quality, units and time gaps.
2. Segment dedicated-device cycles into active, heating, motor/pump and idle
   phases using measured power and interval lengths.
3. Record duration, peak, total energy, phase features and date.
4. Compare repeats with a similarity heuristic; cluster only after several
   independent valid cycles and user-confirmed labels.
5. For shared whole-house metering, label load events **unknown** until
   a reliable appliance identifier or additional dedicated measurements exist.
6. Never present heuristic similarity as a statistical confidence score.

## Recommendations

Use the appliance's measured time-varying energy profile, a validated local
grid-import estimate, and future regional grid carbon-intensity slots.
Compute estimated emissions for every feasible start time, and compare the
result with running now. Show approximate grams CO2 and kWh of grid import,
source freshness and the latest finish time. Price can be another independent
factor if tariff data are connected. The **regional NESO carbon-intensity
forecast** is a candidate input, but remains optional and must be labelled
unavailable when the network is offline.

Do not schedule noisy appliances during quiet hours or any appliance unattended
when manufacturer guidance or safety require supervision. Dishwasher/washing
machine delay controls depend on their hardware capabilities and owner approval.
The first iteration only **suggests** start times. No unattended on/off control,
no automatic service calls, no high-load relay switching.

## Current state

`energy_learning.py` contains pure, tested building blocks. The HA runtime
event listener, measured-cycle database, named-appliance labels and user-facing
suggestion cards are **not yet implemented**. Do not claim fingerprint detection
is enabled until a real validated appliance sensor supplies measurements.
