class Player:
    def __init__(self, name, is_human):
        self.name = name
        self.is_human = is_human
        self.role = None # Le rôle sera assigné plus tard
        self.is_alive = True
        self.has_saved_potion = True # Pour la Sorcière
        self.has_kill_potion = True  # Pour la Sorcière
        self.has_seen_role = None # Pour la Voyante (le rôle vu lors de la nuit)
        self.is_attacked_this_night = False # Pour savoir si la Sorcière peut sauver

    def __str__(self):
        # Représentation textuelle du joueur
        status = "Vivant" if self.is_alive else "Mort"
        return f"{self.name} ({status})"

    def assign_role(self, role):
        self.role = role

    def die(self):
        self.is_alive = False

    # Méthodes spécifiques aux rôles seront gérées dans la logique du jeu,
    # mais on peut ajouter des drapeaux ou des données ici.