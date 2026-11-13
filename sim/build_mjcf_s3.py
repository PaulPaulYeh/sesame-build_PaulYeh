"""Generate models/sesame.xml for THIS robot: the S3 build on the V3 internal frame.

Student body profile (single-OLED V3 kit, assets/printing/internal-frame-s3).
The reference generator `sim/build_mjcf.py` describes the original upstream
v121 body and stays untouched (its hash is pinned by the body-provenance audit).
This module reuses its joint conventions, leg link lengths and actuator model,
and only replaces the torso:

- Torso meshes: V3 internal frame, bottom cover, head shell and lid. The V3 STLs
  are already in the simulator's torso-local frame (x front/OLED, y left, z up,
  millimetres; frame z -10.73..4.97 mm matches the upstream frame exactly), so
  they are only scaled to metres.
- Hip axes: native V3 servo mounts, frame-datums.json `hip_shaft_xy_mm`
  (front x +28.22, back x -28.58, |y| 37.975 mm). The frame is wider and longer
  than the upstream one; the eight leg parts and servo bay depth are unchanged.
- Masses: estimates (slicer filament weights + nominal servo/battery/electronics)
  until the robot is weighed (NEEDS-HARDWARE).

Usage:
  uv run python -m sim.build_mjcf_s3 --meshes   # (re)convert V3 meshes + rewrite XML
  uv run python -m sim.build_mjcf_s3            # rewrite models/sesame.xml only
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sim import build_mjcf as ref
from sim.manifest import Manifest, load_manifest

REPO = Path(__file__).parent.parent
MODEL_PATH = ref.MODEL_PATH
V3_DIR = REPO / "assets" / "printing" / "internal-frame-s3"
MESH_OUT = REPO / "assets" / "mesh"
GLB_OUT = REPO / "web" / "public" / "meshes"

# output mesh name -> V3 assembly-coordinate STL (mm)
TORSO_MESHES = {
    "s3_frame": "internal-frame.stl",
    "s3_bottom": "bottom-cover.stl",
    "s3_head": "head-cover.stl",
    "s3_lid": "head-lid.stl",
}

# Hip shaft positions (m), from internal-frame-s3/frame-datums.json.
HIP_X_FRONT = 0.028217
HIP_X_BACK = -0.028584
HIP_Y = 0.037975
LEG_PLANE_DZ = ref.LEG_PLANE_DZ  # same servo flange seat as upstream frame
UPPER_LEN = ref.UPPER_LEN
FOOT_LEN = ref.FOOT_LEN
SPAWN_Z = ref.SPAWN_Z  # bottom cover still at z = -18.0 mm

# Collision boxes (center, half-size), metres. Base = frame + bottom cover,
# head = shell incl. ears (measured STL bounds).
BASE_POS = (0.000115, 0.0, -0.006515)
BASE_HALF = (0.043590, 0.039700, 0.011485)
HEAD_POS = (0.000115, 0.0, 0.031855)
HEAD_HALF = (0.043590, 0.029270, 0.026885)
# Estimated: frame+spacers 45 g, bottom ~15 g, 4 hip servos 54 g, battery 47 g,
# carrier/S3/PCA9685/wiring ~20 g in the base; head+lid 42 g + OLED ~3 g on top.
BASE_MASS = 0.181
HEAD_MASS = 0.045
FACE_POS = (0.0437, 0.0, 0.030)  # blue OLED marker on the head front (approx.)
# The face/rear sites stay level (z = 4 mm) at the torso ends: telemetry's
# pitch signal is their height difference, so they must not be offset.


def convert_meshes() -> None:
    import trimesh

    MESH_OUT.mkdir(parents=True, exist_ok=True)
    GLB_OUT.mkdir(parents=True, exist_ok=True)
    for name, src in TORSO_MESHES.items():
        mesh = trimesh.load(V3_DIR / src)
        out = trimesh.Trimesh(vertices=mesh.vertices / 1000.0, faces=mesh.faces, process=False)
        out.export(MESH_OUT / f"{name}.stl")
        out.export(GLB_OUT / f"{name}.glb")
        print(f"wrote {name}: assets/mesh/{name}.stl + web/public/meshes/{name}.glb")


def _leg_xml(m: Manifest, hip_name: str, foot_name: str) -> str:
    hip = m.joint(hip_name)
    fx = HIP_X_FRONT if "front" in hip.leg else HIP_X_BACK
    sy = 1.0 if "left" in hip.leg else -1.0
    # Reuse the reference leg block verbatim, then move its hip anchor.
    block = ref._leg_xml(m, hip_name, foot_name)
    old = (f'pos="{(1.0 if "front" in hip.leg else -1.0) * ref.HIP_X:.4f} '
           f'{sy * ref.HIP_Y:.4f} {ref.LEG_PLANE_DZ}"')
    new = f'pos="{fx:.6f} {sy * HIP_Y:.6f} {LEG_PLANE_DZ}"'
    assert block.count(old) == 1, "reference leg layout changed"
    return block.replace(old, new)


def _f(v: tuple[float, ...]) -> str:
    return " ".join(f"{x:.6f}" for x in v)


def build_xml(m: Manifest | None = None) -> str:
    m = m or load_manifest()
    by_leg = {j.leg: {} for j in m.joints}
    for j in m.joints:
        by_leg[j.leg][j.role] = j.name
    legs = "".join(_leg_xml(m, n["hip"], n["foot"]) for n in by_leg.values())
    leg_meshes = [n for n in ref.MESH_NAMES if not n.startswith("torso_")]
    meshes = "".join(
        f'\n    <mesh name="{n}" file="{n}.stl"/>' for n in [*TORSO_MESHES, *leg_meshes]
    )
    visuals = "".join(
        f"""
      <geom name="{n}_visual" type="mesh" mesh="{n}" mass="0"
            group="2" contype="0" conaffinity="0" rgba="{ref.BODY_RGBA}"/>"""
        for n in TORSO_MESHES
    )
    actuators = "".join(
        f"""
    <position name="{j.name}" joint="{j.name}" kp="{ref.ACT_KP}"
              forcerange="-{ref.ACT_FORCE} {ref.ACT_FORCE}"
              ctrlrange="{m.internal_range(j)[0]:.6f} {m.internal_range(j)[1]:.6f}"/>"""
        for j in m.joints
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED from manifest/robot.yaml by sim/build_mjcf_s3.py — do not edit by hand.
     Student S3 build: V3 internal frame (single OLED). Legs from upstream v117;
     torso from assets/printing/internal-frame-s3; masses estimated. -->
<mujoco model="sesame">
  <option timestep="{ref.TIMESTEP}"/>
  <compiler angle="radian" autolimits="true" meshdir="../assets/mesh"/>
  <default>
    <geom friction="0.9 0.005 0.0001" condim="3"/>
    <site size="0.0025" rgba="0.1 0.9 0.3 0.6"/>
  </default>
  <asset>{meshes}
  </asset>
  <worldbody>
    <light pos="0 0 1.5" dir="0 0 -1"/>
    <geom name="floor" type="plane" size="2 2 0.05" rgba="0.85 0.85 0.85 1"/>
    <body name="torso" pos="0 0 {SPAWN_Z}">
      <freejoint name="root"/>
      <geom name="torso_geom" type="box" pos="{_f(BASE_POS)}" size="{_f(BASE_HALF)}"
            mass="{BASE_MASS}" group="3" rgba="0.9 0.75 0.5 1"/>
      <geom name="head_geom" type="box" pos="{_f(HEAD_POS)}" size="{_f(HEAD_HALF)}"
            mass="{HEAD_MASS}" group="3" rgba="0.9 0.75 0.5 1"/>{visuals}
      <geom name="face_geom" type="box" size="0.002 0.0115 0.006"
            pos="{_f(FACE_POS)}" mass="0.001"
            contype="0" conaffinity="0" rgba="0.15 0.2 0.9 1"/>
      <site name="torso_center" pos="0 0 0"/>
      <site name="face" pos="{HEAD_POS[0] + HEAD_HALF[0]:.6f} 0 0.004"/>
      <site name="rear" pos="{HEAD_POS[0] - HEAD_HALF[0]:.6f} 0 0.004"/>{legs}
    </body>
  </worldbody>
  <actuator>{actuators}
  </actuator>
</mujoco>
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--meshes", action="store_true", help="also convert the V3 torso meshes")
    args = p.parse_args()
    if args.meshes:
        convert_meshes()
    MODEL_PATH.write_text(build_xml(), encoding="utf-8", newline="\n")
    print(f"wrote {MODEL_PATH}")


if __name__ == "__main__":
    main()
