import math
import params
from utils import get_distance

class Muscle:
    def __init__(self, n_center, n_target, freq, phase, amplitude):
        self.n_center = n_center
        self.n_target = n_target
        self.freq = freq
        self.phase = phase
        self.amplitude = amplitude
        self.length = params.SEGMENT_LENGTH
        self.energy_spent = 0

    def apply_physics(self, nodes, timer):
        nc, nt = nodes[self.n_center], nodes[self.n_target]
        
        # 1. Rotation forcée
        target_angle = math.sin(timer * self.freq + self.phase) * self.amplitude
        dx, dy = nt.x - nc.x, nt.y - nc.y
        current_angle = math.atan2(dy, dx)
        diff = (target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
        
        torque = diff * 0.3
        self.energy_spent += abs(torque) * self.freq

        # 2. Propulsion Newtonienne
        perp_x, perp_y = -dy / self.length, dx / self.length
        push = torque * params.WATER_DENSITY
        nt.vx += perp_x * push
        nt.vy += perp_y * push
        nc.vx -= perp_x * push
        nc.vy -= perp_y * push

        # 3. Contrainte de distance rigide
        new_dx, new_dy = nt.x - nc.x, nt.y - nc.y
        new_dist = math.sqrt(new_dx**2 + new_dy**2)
        if new_dist == 0: return
        corr = (self.length - new_dist) / new_dist
        nt.x += new_dx * corr * 0.5
        nt.y += new_dy * corr * 0.5
        nc.x -= new_dx * corr * 0.5
        nc.y -= new_dy * corr * 0.5