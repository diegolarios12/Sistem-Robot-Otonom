# ============================================
# P3DX — Numpy transform + (optional) CoppeliaSim push
# ============================================
import math
import numpy as np

# ---------- Core math ----------
def deg2rad(d): 
    return d * math.pi / 180.0

def Rz(gamma_deg: float) -> np.ndarray:
    """Rotation about Z by gamma (deg)."""
    g = deg2rad(gamma_deg)
    c, s = math.cos(g), math.sin(g)
    return np.array([[ c, -s, 0.0],
                     [ s,  c, 0.0],
                     [0.0, 0.0, 1.0]], dtype=float)

def make_T_B_U(alpha_deg: float, beta_deg: float, gamma_deg: float,
               tx: float, ty: float, tz: float) -> np.ndarray:
    """
    Build homogeneous transform ^B T_U using Z-rotation only (per tugas).
    If later you need full XYZ-Euler, extend here.
    """
    # In the assignment only gamma (yaw) is non-zero.
    R = Rz(gamma_deg)
    t = np.array([[tx], [ty], [tz]], dtype=float)
    T = np.eye(4, dtype=float)
    T[:3, :3] = R
    T[:3, 3:4] = t
    return T

def to_h(p_xyz: tuple|list|np.ndarray) -> np.ndarray:
    """R^3 -> homogeneous R^4 column."""
    p = np.array(p_xyz, dtype=float).reshape(3, 1)
    return np.vstack([p, [[1.0]]])

def from_h(ph: np.ndarray) -> np.ndarray:
    """Homogeneous column -> R^3 row."""
    return (ph[:3, 0] / ph[3, 0])

def transform_point(T: np.ndarray, pU_xyz: tuple|list|np.ndarray) -> np.ndarray:
    """Compute p_B = ^B T_U * p_U"""
    return from_h(T @ to_h(pU_xyz))

# ---------- Cases from the slide ----------
alpha, beta, gamma = 0.0, 0.0, 90.0
tx, ty, tz = 0.0, 0.0, 0.0

cases = [
    {"name": "A", "u": (2, 0, 0), "euler": (alpha, beta, gamma)},
    {"name": "B", "u": (0, 2, 0), "euler": (alpha, beta, gamma)},
    {"name": "C", "u": (2, 0, 2), "euler": (alpha, beta, gamma)},
    {"name": "D", "u": (2, 0, 2), "euler": (0.0, 0.0, -180.0)},
]

T_cache = {}  # cache per (alpha,beta,gamma,tx,ty,tz)

print("=== Perhitungan koordinat p di basis B ===")
print(f"(tx,ty,tz)=({tx:.1f},{ty:.1f},{tz:.1f})")
print("{:>3s} | {:>14s} | {:>14s} | {:>14s}".format(
    "ID", "(u_xp,u_yp,u_zp)", "(alpha,beta,gamma)", "(B_xp,B_yp,B_zp)"))
print("-"*60)

results = {}
for c in cases:
    a,b,g = c["euler"]
    key = (a,b,g,tx,ty,tz)
    if key not in T_cache:
        T_cache[key] = make_T_B_U(a,b,g,tx,ty,tz)
    T = T_cache[key]
    pB = transform_point(T, c["u"])
    results[c["name"]] = {"u": np.array(c["u"], float),
                          "euler": (a,b,g),
                          "B": pB.copy()}
    print("{:>3s} | {:>14s} | {:>14s} | {:>14s}".format(
        c["name"],
        str(tuple(c["u"])),
        str(tuple(map(float, c["euler"]))),
        str(tuple(np.round(pB, 6)))))
    
# ---------- Optional: push to CoppeliaSim ----------
PUSH_TO_COPPELIA = False  # set True to actually push poses

if PUSH_TO_COPPELIA:
    # You need CoppeliaSim running with the ZMQ remote API service enabled
    # (Menu: Add-on scripts -> ZMQ remote API).
    from coppeliasim_zmqremoteapi_client import RemoteAPIClient
    client = RemoteAPIClient()
    sim = client.getObject('sim')

    # Handles (adjust paths to your scene):
    # - P3DX base (e.g., '/PioneerP3DX')
    # - a dummy object to visualize the transformed point in world (e.g., '/targetPoint')
    p3dx = sim.getObject('/PioneerP3DX')          # <-- sesuaikan
    point_dummy = sim.getObject('/targetPoint')   # <-- sesuaikan

    # Choose which case to visualize:
    CASE_TO_SHOW = 'C'
    entry = results[CASE_TO_SHOW]
    a,b,g = entry["euler"]
    T = make_T_B_U(a,b,g,tx,ty,tz)

    # Set P3DX pose: only yaw (gamma) around world Z, position t
    # setObjectPosition/Orientation expect radians and absolute reference (-1)
    sim.setObjectPosition(p3dx, -1, [tx, ty, tz])
    sim.setObjectOrientation(p3dx, -1, [deg2rad(a), deg2rad(b), deg2rad(g)])

    # Place dummy at transformed point in world/B frame
    pB = entry["B"]
    sim.setObjectPosition(point_dummy, -1, pB.tolist())

    print(f"[CoppeliaSim] Menampilkan kasus {CASE_TO_SHOW}: "
          f"u={tuple(entry['u'])} -> B={tuple(np.round(pB,6))}, yaw={g}°")
