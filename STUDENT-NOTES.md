# Sesame S3 build notes — PaulYeh

Base: sim2real `1bb88dd1f40cb40c01508deaaa0aeed472aed1b4` (merged into this repo; remote `upstream`).

## Windows build setup (2026-11-08)

- Python 3.12.10, Git 2.56, uv 0.13.7 (winget); arduino-cli 1.5.1 from the official
  release zip, SHA256 checked against `1.5.1-checksums.txt`.
- `git config core.autocrlf false` in this repo — CRLF checkout breaks the vendored
  and manifest hash checks.
- Set `PYTHONUTF8=1` before `tools/sesame_s3.py` — the cp950 locale cannot read the UTF-8 YAML.
- Board: ESP32-S3 on COM6.

## Clock calibration (Step 29)

| | oscillator setting | measured PWM |
|---|---|---|
| default | 25 000 000 Hz | 55.45 Hz (estimate 27 709 852.59 Hz) |
| applied + saved | 27 709 852 Hz (prescale 134) | 50.009 Hz (re-measure estimate 27 652 894.56 Hz) |

Reference is the S3 esp_timer, not a lab standard.

## Servo calibration (Step 31)

Map is the default (L1=CH0 … R4=CH7); signs unchanged. Bench sweeps 0→90→180→90 on all
eight: full travel observed by student. Trim chosen by student as the bench angle that
looked like true 90°:

| joint | L1 | L2 | L3 | L4 | R1 | R2 | R3 | R4 |
|---|---|---|---|---|---|---|---|---|
| trim ° | 0 | −10 | −5 | −5 | −5 | −7 | −7 | −8 |

Limits widened to the firmware soft bounds (bench showed full travel; no legs yet):
L1/R2 0–135, L2/R1 45–180, feet 0–180. Joint-mode 45→90→135→90 re-check with 6 s holds:
student confirmed horns at 90°. All eight `verify` + `save`. Exports in `calibration/`.

## Load test

- USB only, all eight 60↔120: **brownout reset** (`E BOD: Brownout detector was triggered`)
  on the 3rd–4th swing, twice. USB cannot supply all eight servos.
- Phone web console on battery: `ERR arm run first` — heartbeat lease dropped.
- Added firmware `loadtest` command + web buttons (below). On battery:
  `LOADTEST runs=2 active=0 result=ended: loadtest complete after 10265ms uptime_ms=125859`
  — completed, no reset during the run.

## Firmware changes vs upstream

`controller.cpp`, `web_ui.h`: `loadtest` (OFF only; needs all joints verified+saved) runs
90, (60,120)×3, 90 on all eight with 1 s holds, renews its own heartbeat, then turns
outputs OFF. Aborted by `off`, BOOT, or a 30 s limit. `loadtest status` reports runs,
result and uptime (a small uptime with `none since boot` means a reset). `manifest/` is
untouched, so the manifest ID and saved calibration stay compatible.

## Next

Leg assembly (Steps 33–34) at the 90° mounting pose. Limits may need narrowing after
legs are fitted.
