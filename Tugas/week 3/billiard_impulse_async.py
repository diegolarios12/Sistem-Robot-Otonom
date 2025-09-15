"""
billiard_impulse_async_fixed.py
- CoppeliaSim 4.10.0 + zmqRemoteApi
- Pakai scene yang SUDAH TERBUKA
- Mode ASINKRON (tanpa stepping sinkron)
- Input terminal: gaya (N) & torsi (N·m) dalam KOORDINAT GLOBAL
- Setiap input = impuls SEKALI (1 langkah dinamika)
- Target default: 'sphere 6'
- Skala panjang scene: 1 unit = 0.001 m (mm). Force (N) dipakai langsung; Torque (N·m) dikonversi ke N·unit.

pip install coppeliasim-zmqremoteapi-client
"""

import argparse
from typing import List

try:
    from coppeliasim_zmqremoteapi_client import RemoteAPIClient
except ImportError:
    raise SystemExit(
        "Package 'coppeliasim-zmqremoteapi-client' tidak ditemukan.\n"
        "Instal dengan: pip install coppeliasim-zmqremoteapi-client"
    )

DEFAULT_TARGET_NAME = "Sphere[6]"

def connect(host: str, port: int):
    client = RemoteAPIClient(host=host, port=port)
    sim = client.getObject('sim')
    return client, sim

def get_all_dynamic_shapes(sim) -> List[int]:
    """Enumerasi semua shape di scene (aman untuk 4.10) lalu filter yang dinamis."""
    handles = sim.getObjectsInTree(sim.handle_scene, sim.object_shape_type, 0)  # semua shape
    dyn_shapes = []
    for h in handles:
        try:
            dyn = sim.getObjectInt32Param(h, sim.shapeintparam_dynamic)
            if dyn != 0:
                dyn_shapes.append(h)
        except Exception:
            pass
    return dyn_shapes

def find_object_by_name(sim, desired_name: str) -> int:
    """
    Cari handle berdasarkan alias:
      - Coba path absolut: '/<alias>'
      - Kalau gagal, telusuri semua shape dinamis & samakan nama (case-insensitive)
      - Jika masih gagal, tampilkan kandidat yang mengandung teks
    """
    # 1) Path absolut (paling akurat di 4.x):
    for candidate in (f'/{desired_name}', desired_name):
        try:
            h = sim.getObject(candidate)
            return h
        except Exception:
            pass

    # 2) Enumerasi shape dinamis & cocokkan alias:
    matches_eq = []
    matches_sub = []
    name_l = desired_name.lower()
    for h in get_all_dynamic_shapes(sim):
        try:
            alias = sim.getObjectAlias(h, 1)  # unique alias
        except Exception:
            continue
        if not alias:
            continue
        alias_l = alias.lower()
        if alias_l == name_l:
            matches_eq.append(h)
        elif name_l in alias_l:
            matches_sub.append(h)

    if matches_eq:
        return matches_eq[0]
    if matches_sub:
        # Ambil kandidat pertama yang "mengandung" nama
        return matches_sub[0]

    # 3) Kalau benar-benar tidak ketemu, lempar error dengan daftar bola dinamis
    all_dyn = get_all_dynamic_shapes(sim)
    cand = []
    for h in all_dyn:
        try:
            cand.append(sim.getObjectAlias(h, 1))
        except Exception:
            pass
    raise RuntimeError(
        f"Tidak menemukan objek bernama '{desired_name}'. "
        f"Kandidat dinamis di scene: {', '.join(a for a in cand if a)}"
    )

def ask_force_torque_global() -> tuple[list[float], list[float]]:
    print("\nMasukkan gaya (N) dan torsi (N·m) dalam KOORDINAT GLOBAL.")
    print("Enter = 0. Contoh pukulan mendatar: Fx=5, Fy=0, Fz=0")
    def readf(label: str) -> float:
        s = input(f"{label} = ").strip()
        return float(s) if s else 0.0
    Fx = readf("Fx [N]")
    Fy = readf("Fy [N]")
    Fz = readf("Fz [N]")
    Tx = readf("Tx [N·m]")
    Ty = readf("Ty [N·m]")
    Tz = readf("Tz [N·m]")
    return [Fx, Fy, Fz], [Tx, Ty, Tz]

def main():
    ap = argparse.ArgumentParser(description="Impuls gaya/torsi global ke bola billiard (asinkron).")
    ap.add_argument("--host", default="127.0.0.1", help="Host ZeroMQ (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=23000, help="Port ZeroMQ (default: 23000)")
    ap.add_argument("--target", default=DEFAULT_TARGET_NAME, help=f"Nama objek target (default: '{DEFAULT_TARGET_NAME}')")
    ap.add_argument("--length-scale", type=float, default=0.001,
                    help="Meter per unit (default: 0.001 m/unit untuk mm-scene)")
    args = ap.parse_args()

    client, sim = connect(args.host, args.port)

    # Pastikan simulasi berjalan (asinkron)
    state = sim.getSimulationState()
    if state == sim.simulation_stopped:
        print("[i] Simulasi belum berjalan. Menjalankan simulasi...")
        sim.startSimulation()
    else:
        print("[i] Simulasi sudah berjalan (asinkron).")

    # Pastikan asinkron (non stepping)
    try:
        sim.setStepping(False)
    except Exception:
        pass

    # Cari target
    try:
        target = find_object_by_name(sim, args.target)
    except RuntimeError as e:
        print(f"(!) {e}")
        # Opsi tambahan: list semua shape dinamis agar user tahu nama pasti
        print("\n[i] Daftar shape dinamis (untuk referensi):")
        for h in get_all_dynamic_shapes(sim):
            try:
                print(" -", sim.getObjectAlias(h, 1))
            except Exception:
                pass
        return

    target_name = sim.getObjectAlias(target, 1)
    print(f"[i] Target: {target_name} (handle {target})")
    print(f"[i] Length scale: {args.length_scale} m/unit (mm-scene). "
          f"Torsi SI akan dibagi {args.length_scale} -> N·unit.")

    print("\n=== Mode impuls (sekedip) ===")
    print("Ketik 'q' untuk keluar. Tiap input diterapkan SATU KALI (1 langkah).")
    while True:
        cmd = input("\nLanjut input (Enter) atau 'q' untuk keluar? ").strip().lower()
        if cmd == 'q':
            break

        force_SI, torque_SI = ask_force_torque_global()

        # Konversi ke unit scene
        force_scene = force_SI[:]  # N apa adanya
        if args.length_scale <= 0:
            torque_scene = torque_SI[:]
        else:
            inv_scale = 1.0 / args.length_scale
            torque_scene = [t * inv_scale for t in torque_SI]

        print(f"[i] Apply (global): F={force_SI} N, T={torque_SI} N·m "
              f"-> scene torque={torque_scene} N·unit")

        # Impuls satu kali
        sim.addForceAndTorque(target, force_scene, torque_scene)
        print("[i] Impuls dikirim.")

    print("[i] Selesai. Simulasi tetap berjalan.")

main()