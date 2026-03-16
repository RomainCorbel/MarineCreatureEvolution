

# Creature Evolution Simulator


## Installation Rapide

Suivez ces étapes pour configurer votre environnement de développement :

### 1. Cloner le dépôt
```bash
git clone https://github.com/RomainCorbel/MarineCreatureEvolution.git
cd MarineCreatureEvolution
```
### 2. Créer l'environnement Conda
Ouvrez un terminal dans le dossier du projet et exécutez :
```bash
conda env create -f environment.yml
```

### 3. Activer l'environnement

```bash
conda activate creature_sim
```

### 4. Configuration GPU si dispo

```bash
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

---

## Structure du Projet

* **`main.py`** : Point d'entrée. Lance la boucle Pygame et gère l'affichage.
* **`creature.py`** : Définit les classes `Node` (physique) et `Creature` (structure).
* **`movement.py`** : Contient la classe `Muscle` et la logique de propulsion.
* **`params.py`** : Toutes les constantes (Gravité, FPS, Population, etc.).
* **`utils.py`** : Fonctions mathématiques et utilitaires de collision.

---

## Utilisation

Pour lancer la simulation standard :

```bash
python main.py
```