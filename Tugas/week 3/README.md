# Simulasi Biliar dengan CoppeliaSim dan Python

Proyek ini merupakan simulasi meja biliar menggunakan **CoppeliaSim** dan **Python**. 
Bola biliar dapat digerakkan dengan memberikan gaya (force) atau torsi (torque) melalui skrip Python 
yang terhubung ke CoppeliaSim menggunakan **ZeroMQ Remote API**.

## Struktur Project
- `Billiard.ttt` → File scene simulasi untuk CoppeliaSim.
- `billiard_impulse_async.py` → Skrip Python untuk memberi impuls gaya/torsi pada bola.

## Persyaratan
- [CoppeliaSim](https://www.coppeliarobotics.com/downloads)
- Python 3.x
- Library tambahan:
  ```bash
  pip install coppeliasim-zmqremoteapi-client
