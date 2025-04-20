class Role:
    def __init__(self, name, description, team="Village", can_act_night=False, is_wolf=False, is_special=False):
        self.name = name
        self.description = description
        self.team = team # "Village", "Loups", "Solitaire" (pour futures versions)
        self.can_act_night = can_act_night # Si le rôle a une action la nuit
        self.is_wolf = is_wolf
        self.is_special = is_special # Vrai pour tous sauf Villageois/Loups de base

# Définition des rôles initiaux
ROLES_LIST = {
    "Villageois": Role("Villageois", "Simple habitant du village."),
    "Loup-Garou": Role("Loup-Garou", "Dévoré un villageois chaque nuit.", team="Loups", can_act_night=True, is_wolf=True),
    "Voyante": Role("Voyante", "Découvre l'identité d'un joueur chaque nuit.", can_act_night=True, is_special=True),
    "Sorcière": Role("Sorcière", "Possède une potion de vie et une potion de mort.", can_act_night=True, is_special=True),
    "Chasseur": Role("Chasseur", "Élimine un joueur en mourant.", is_special=True)
    # Petite Fille non incluse pour la V1 simple
}

# Fonction pour obtenir un rôle par son nom
def get_role(name):
    return ROLES_LIST.get(name)

# Fonction pour obtenir la liste des rôles disponibles pour la config
def get_available_roles():
    return list(ROLES_LIST.keys())