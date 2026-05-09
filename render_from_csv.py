"""
render_from_csv.py — Render a simulation video for a specific line of a CSV file.

Usage:
  python render_from_csv.py <csv_file> <line_number>

  line_number is the line in the file (1 = header, so first data row = 2).

Example:
  python render_from_csv.py evolution_20260509_143510.csv 1001
"""

import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import sys, math, time
import numpy as np

from jellyfish_ga import (
    render_generation, open_video,
    FPS, WIDTH, HEIGHT,
)

_COLS = [
    'gen', 'best_fitness', 'avg_fitness', 'min_fitness',
    'best_energy', 'avg_energy', 'min_energy',
    'best_distance', 'avg_distance', 'min_distance',
    'member', 'amplitude', 'period', 'duty_cycle',
    'arm_angle_deg', 'arm_length',
    'member_fitness', 'member_distance', 'member_energy',
]


def main():
    if len(sys.argv) != 3:
        print("Usage: python render_from_csv.py <csv_file> <line_number>")
        print("       line_number: 1 = header, first data row = 2")
        sys.exit(1)

    csv_path   = sys.argv[1]
    line_number = int(sys.argv[2])

    with open(csv_path, 'r') as f:
        lines = f.readlines()

    if line_number < 2 or line_number > len(lines):
        print(f"ERROR: line {line_number} is out of range (file has {len(lines)} lines, line 1 is the header).")
        sys.exit(1)

    parts = [p.strip() for p in lines[line_number - 1].strip().split(',')]
    if len(parts) != len(_COLS):
        print(f"ERROR: expected {len(_COLS)} columns, got {len(parts)}.")
        sys.exit(1)

    row = {k: parts[i] for i, k in enumerate(_COLS)}

    gen      = int(float(row['gen']))
    member   = int(float(row['member']))
    fitness  = float(row['member_fitness'])
    distance = float(row['member_distance'])
    energy   = float(row['member_energy'])

    genome = np.array([
        float(row['amplitude']),
        float(int(float(row['period']))),
        float(row['duty_cycle']),
        math.radians(float(row['arm_angle_deg'])),
        float(row['arm_length']),
    ], dtype=np.float64)

    freq_hz = FPS / genome[1]
    print(f"\n  File    : {csv_path}  (line {line_number})")
    print(f"  Gen {gen}  |  Member {member}")
    print(f"  amplitude  = {genome[0]:.4f} rad")
    print(f"  period     = {int(genome[1])} frames  ({freq_hz:.3f} Hz)")
    print(f"  duty_cycle = {genome[2]:.4f}")
    print(f"  arm_angle  = {math.degrees(genome[3]):.2f}°")
    print(f"  arm_length = {genome[4]:.4f}")
    print(f"  fitness    = {fitness:.5f}  |  distance = {distance:.3f}  |  energy = {energy:.3f}\n")

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.dirname(os.path.abspath(csv_path))
    out_path = os.path.join(out_dir, f"render_gen{gen:03d}_m{member:03d}_{ts}.mp4")
    print(f"  Output → {out_path}\n")

    import pygame
    pygame.init()
    surface = pygame.Surface((WIDTH, HEIGHT))
    font    = pygame.font.SysFont(None, 26)

    history     = {'best': [fitness]}
    gen_label   = f"{gen}  (member {member})"
    ffmpeg_proc = open_video(out_path)

    print("Rendering...", end='', flush=True)
    render_generation(genome, gen_label, fitness, distance,
                      history, surface, font, ffmpeg_proc)
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()
    pygame.quit()

    print(" done.")
    print(f"Video saved → {out_path}")


if __name__ == '__main__':
    main()
