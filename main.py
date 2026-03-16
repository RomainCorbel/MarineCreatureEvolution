import pygame
import params
from creature import Node, Creature
from movement import Muscle

def spawn():
    n = [Node(-params.SEGMENT_LENGTH/2, 0), Node(params.SEGMENT_LENGTH/2, 0)]
    m = [Muscle(0, 1, 0.1, 0, 0.8)]
    return Creature(n, m)

def main():
    pygame.init()
    screen = pygame.display.set_mode((params.WINDOW_WIDTH, params.WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    
    population = [spawn() for _ in range(params.POPULATION_SIZE)]
    gen, timer = 0, 0
    
    while True:
        screen.fill(params.COLOR_BG)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return

        for c in population: c.update(timer)
        leader = max(population, key=lambda c: c.calculate_fitness())
        
        # Rendu
        zoom, ox, oy = 100, 400, 360
        for m in leader.muscles:
            n1, n2 = leader.nodes[m.n_center], leader.nodes[m.n_target]
            pygame.draw.line(screen, params.COLOR_MUSCLE, 
                             (n1.x*zoom+ox, n1.y*zoom+oy), 
                             (n2.x*zoom+ox, n2.y*zoom+oy), 8)
        for n in leader.nodes:
            pygame.draw.circle(screen, params.COLOR_NODE, 
                               (int(n.x*zoom+ox), int(n.y*zoom+oy)), 
                               int(params.NODE_RADIUS*zoom))

        timer += 1
        if timer > params.GEN_DURATION:
            population.sort(key=lambda c: c.calculate_fitness(), reverse=True)
            survivors = population[:params.POPULATION_SIZE//2]
            new_gen = []
            for s in survivors:
                for n in s.nodes: n.reset()
                for m in s.muscles: m.energy_spent = 0
                new_gen.append(s)
                new_gen.append(s.mutate())
            population = new_gen
            gen += 1; timer = 0
            print(f"Gen {gen} | Fitness: {leader.fitness:.2f} | Segments: {len(leader.muscles)}")

        pygame.display.flip()
        clock.tick(params.FPS)

if __name__ == "__main__":
    main()