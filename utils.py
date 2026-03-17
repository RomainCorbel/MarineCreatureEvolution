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
    """Génère un rapport détaillé incluant l'ancêtre et les stats."""
    total_dist = sum(n.x for n in creature.nodes) / len(creature.nodes)
    total_energy = sum(m.energy_spent for m in creature.muscles)
    n_muscles = len(creature.muscles)
    std_energy = total_energy / n_muscles if n_muscles > 0 else 0
    
    stats = []
    stats.append(f"=== Creature Report [Lignée: {creature.ancestor_id}] ===")
    stats.append(f"Fitness Score : {creature.fitness:.2f}")
    stats.append(f"Distance      : {creature.distance:.2f} m")
    stats.append(f"Total Energy  : {creature.energie_totale:.2f}")
    stats.append(f"Normalized Energy : {creature.energie_normalisee:.2f}")
    stats.append(f"Structure     : {len(creature.nodes)} Nodes | {n_muscles} Muscles")
    stats.append("-" * 35)
    
    for i, m in enumerate(creature.muscles):
        stats.append(f" Muscle {i} [N{m.n_center}-N{m.n_target}]: F={m.freq:.2f}, P={m.phase:.2f}, A={m.amplitude:.2f}")
    
    return "\n".join(stats)

def save_creature_to_csv(creature, gen, ranking, filename="creatures_data.csv"):
    """Enregistre les stats d'une créature incluant son rang dans la génération."""
    
    total_dist = sum(n.x for n in creature.nodes) / len(creature.nodes)
    total_energy = sum(m.energy_spent for m in creature.muscles)
    n_muscles = len(creature.muscles)
    std_energy = total_energy / n_muscles if n_muscles > 0 else 0

    file_exists = os.path.isfile(filename)
    
    # Ajout de la colonne "ranking"
    headers = [
        "generation", "ranking", "ancestor_id", "fitness", "distance", 
        "total_energy", "num_nodes", "num_muscles", "muscle_data"
    ]
    
    muscle_dna = "|".join([
        f"M{i}({m.n_center}-{m.n_target}:F={m.freq:.2f},P={m.phase:.2f},A={m.amplitude:.2f})"
        for i, m in enumerate(creature.muscles)
    ])

    data = [
        gen,
        ranking,               # Nouveau : 1 pour le meilleur, 100 pour le dernier
        creature.ancestor_id,
        round(creature.fitness, 4),
        round(total_dist, 4),
        round(total_energy, 4),
        round(std_energy, 4),
        len(creature.nodes),
        n_muscles,
        muscle_dna
    ]

    with open(filename, mode='a', newline='', encoding='utf-16') as f:
        writer = csv.writer(f, delimiter='\t')
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(data)