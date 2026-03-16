import math

def intersect(p1, p2, p3, p4):
    """ Vérifie si le segment (p1,p2) croise (p3,p4) """
    def ccw(A, B, C):
        return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)
    
    try:
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
    except AttributeError:
        return False

def get_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# def describe_creature(creature):
#     """ Returns a string containing a full technical breakdown of a creature. """
#     description = []
#     description.append(f"=== Creature Report (Fitness: {creature.fitness:.2f}) ===")
    
#     # Node Info
#     description.append(f"Nodes: {len(creature.nodes)}")
#     for i, node in enumerate(creature.nodes):
#         description.append(f"  [{i}] Initial Pos: ({node.ix:.2f}, {node.iy:.2f}) | Radius: {node.radius}")

#     # Muscle/DNA Info
#     description.append(f"Muscles: {len(creature.muscles)}")
#     for i, m in enumerate(creature.muscles):
#         description.append(f"  Muscle {i}: Node {m.n_center} <-> Node {m.n_target}")
#         description.append(f"    - Frequency: {m.freq:.3f}")
#         description.append(f"    - Phase: {m.phase:.3f}")
#         description.append(f"    - Amplitude: {m.amplitude:.3f}")
#         description.append(f"    - Energy Consumed: {m.energy_spent:.2f}")

#     return "\n".join(description)


def describe_creature(creature):
    """Génère un rapport détaillé incluant la distance, l'énergie et le fitness."""
    # Calculs préalables
    total_dist = sum(n.x for n in creature.nodes) / len(creature.nodes)
    total_energy = sum(m.energy_spent for m in creature.muscles)
    n_muscles = len(creature.muscles)
    
    # Énergie standardisée (on divise par le nombre de muscles pour voir l'efficacité par segment)
    std_energy = total_energy / n_muscles if n_muscles > 0 else 0
    
    stats = []
    stats.append(f"=== Creature Report ===")
    stats.append(f"Fitness Score : {creature.fitness:.2f}")
    stats.append(f"Distance      : {total_dist:.2f} m")
    stats.append(f"Total Energy  : {total_energy:.2f}")
    stats.append(f"Normalized Energy    : {std_energy:.2f} (energy/muscle)")
    stats.append(f"Structure     : {len(creature.nodes)} Nodes | {n_muscles} Muscles")
    stats.append("-" * 25)
    
    # Détails des Muscles (DNA)
    for i, m in enumerate(creature.muscles):
        stats.append(f" Muscle {i} [N{m.n_center}-N{m.n_target}]: Freq={m.freq:.3f}, Phase={m.phase:.2f}, Amp={m.amplitude:.2f}")
    
    return "\n".join(stats)