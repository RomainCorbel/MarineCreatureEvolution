import csv
import math
import os

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

def describe_creature(creature):
    """Génère un rapport adapté au système d'horloge interne."""
    stats = []
    stats.append(f"=== Creature Report [ID: {creature.ancestor_id}] ===")
    stats.append(f"Fitness Score : {creature.fitness:.4f}")
    stats.append(f"Distance      : {creature.distance:.2f}")
    stats.append(f"Energy Spent  : {sum(m.energy_spent for m in creature.muscles):.2f}")
    stats.append(f"Structure     : {len(creature.nodes)} Nodes | {len(creature.muscles)} Muscles")
    stats.append("-" * 35)
    
    for i, m in enumerate(creature.muscles):
        # On affiche la vitesse et le nombre de "pas" dans sa chorégraphie
        stats.append(f" Muscle {i} [N{m.n_center}-N{m.n_target}]: Speed={m.clock_speed:.2f}, Steps={len(m.targets)}")
    
    return "\n".join(stats)

def save_creature_to_csv(creature, gen, ranking, filename="creatures_data.csv"):
    """Enregistre les stats avec le nouvel ADN (clock_speed et targets)."""
    
    n_muscles = len(creature.muscles)
    total_energy = sum(m.energy_spent for m in creature.muscles)
    
    file_exists = os.path.isfile(filename)
    
    headers = [
        "generation", "ranking", "ancestor_id", "fitness", "distance", 
        "total_energy", "num_nodes", "num_muscles", "muscle_dna"
    ]
    
    # Nouveau format d'ADN pour le CSV : Vitesse et nombre de targets
    muscle_dna = "|".join([
        f"M{i}({m.n_center}-{m.n_target}:S={m.clock_speed:.2f},T={len(m.targets)})"
        for i, m in enumerate(creature.muscles)
    ])

    data = [
        gen,
        ranking,
        creature.ancestor_id,
        round(creature.fitness, 4),
        round(creature.distance, 4),
        round(total_energy, 4),
        len(creature.nodes),
        n_muscles,
        muscle_dna
    ]

    with open(filename, mode='a', newline='', encoding='utf-16') as f:
        writer = csv.writer(f, delimiter='\t')
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(data)