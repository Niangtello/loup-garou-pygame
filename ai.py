# ai.py
import random

# Fonction utilitaire pour choisir une cible parmi une liste
def choose_target(potential_targets):
    if not potential_targets:
        return None
    return random.choice(potential_targets)

# --- Logiques IA par rôle ---

class AI_Logic:
    def __init__(self, player, game):
        self.player = player # Le joueur IA associé
        self.game = game     # Référence à l'objet Game

    def decide_night_action(self):
        # Cette méthode sera surchargée par les classes de rôle spécifiques
        pass

    def decide_vote(self):
         # Cette méthode sera surchargée par les classes de rôle spécifiques
         pass

class AI_Villageois(AI_Logic):
    def decide_vote(self):
        # Vote aléatoirement pour un joueur vivant qui n'est pas soi-même
        alive_players = self.game.get_alive_players()
        potential_targets = [p for p in alive_players if p != self.player]
        return choose_target(potential_targets)

class AI_LoupGarou(AI_Logic):
    def decide_night_action(self):
        # Les loups IA se "coordontent" pour choisir une cible aléatoire non-loup
        alive_players = self.game.get_alive_players()
        non_wolves = [p for p in alive_players if not p.role.is_wolf]
        return choose_target(non_wolves) # Retourne le joueur cible

    def decide_vote(self):
        # Vote aléatoirement pour un joueur vivant qui n'est pas un loup
        alive_players = self.game.get_alive_players()
        non_wolves_alive = [p for p in alive_players if not p.role.is_wolf]
        return choose_target(non_wolves_alive)

class AI_Voyante(AI_Logic):
     def decide_night_action(self):
         # Espionne un joueur vivant aléatoirement (qui n'a pas déjà été vu idéalement, mais simple V1 : aléatoire)
         alive_players = self.game.get_alive_players()
         target = choose_target(alive_players)
         if target:
             print(f"DEBUG (IA Voyante {self.player.name}) a vu le rôle de {target.name}: {target.role.name}") # L'IA "sait"
             self.player.has_seen_role = target.role # L'IA stocke l'info
         return target # Retourne le joueur espionné (pour l'affichage MJ si on veut)

     def decide_vote(self):
         # Priorité : si a vu un loup et qu'il est vivant, vote pour lui. Sinon, vote aléatoirement.
         alive_players = self.game.get_alive_players()
         if self.player.has_seen_role and self.player.has_seen_role.is_wolf:
             # Tente de trouver le joueur avec ce rôle vu
             suspected_wolf = next((p for p in alive_players if p.role == self.player.has_seen_role and p.is_alive), None)
             if suspected_wolf and suspected_wolf != self.player:
                 print(f"DEBUG (IA Voyante {self.player.name}) vote pour le loup identifié: {suspected_wolf.name}")
                 return suspected_wolf
         # Si pas de loup identifié ou loup identifié mort, vote aléatoirement
         potential_targets = [p for p in alive_players if p != self.player]
         return choose_target(potential_targets)

class AI_Sorciere(AI_Logic):
     def decide_night_action(self):
         # La sorcière agit APRES les loups et la voyante.
         # L'info sur l'attaque des loups doit lui être passée par le jeu.
         action = {"save": None, "kill": None}

         # Décision de sauver (si potion et si quelqu'un a été attaqué)
         attacked_player = next((p for p in self.game.players if p.is_attacked_this_night and p.is_alive), None) # Le jeu DOIT marquer qui est attaqué
         if self.player.has_saved_potion and attacked_player:
             # Simple règle : 50% de chance de sauver si attaqué, 100% si c'est elle-même
             if attacked_player == self.player or random.random() < 0.5:
                  action["save"] = attacked_player
                  print(f"DEBUG (IA Sorcière {self.player.name}) décide de sauver {attacked_player.name}")
                  # self.player.has_saved_potion = False # La potion est utilisée APRES décision

         # Décision de tuer (si potion et si n'a pas utilisé la potion de vie OU n'en avait pas besoin)
         can_use_kill_potion = self.player.has_kill_potion and action["save"] is None # Peut tuer si potion et pas de save ce tour
         if can_use_kill_potion:
             # Simple règle : 30% de chance de tuer quelqu'un aléatoirement
             if random.random() < 0.3:
                 alive_players = self.game.get_alive_players()
                 potential_targets = [p for p in alive_players if p != self.player]
                 target_to_kill = choose_target(potential_targets)
                 if target_to_kill:
                     action["kill"] = target_to_kill
                     print(f"DEBUG (IA Sorcière {self.player.name}) décide de tuer {target_to_kill.name}")
                     # self.player.has_kill_potion = False # La potion est utilisée APRES décision

         return action # Retourne un dictionnaire {"save": player_to_save, "kill": player_to_kill}

     def decide_vote(self):
         # Vote aléatoirement pour un joueur vivant
         alive_players = self.game.get_alive_players()
         potential_targets = [p for p in alive_players if p != self.player]
         return choose_target(potential_targets)

class AI_Chasseur(AI_Logic):
    # Le chasseur IA n'a pas d'action de nuit ou de vote particulière
    # Son pouvoir s'active quand il meurt, géré dans la logique du jeu principal
    pass # N'a pas d'action à décider pendant la nuit ou le vote normal

# Mapping des rôles aux logiques IA
AI_MAPPING = {
    "Villageois": AI_Villageois,
    "Loup-Garou": AI_LoupGarou,
    "Voyante": AI_Voyante,
    "Sorcière": AI_Sorciere,
    "Chasseur": AI_Chasseur
}

# Fonction pour créer l'objet IA pour un joueur
def create_ai_logic(player, game):
    if player.role and player.role.name in AI_MAPPING:
        return AI_MAPPING[player.role.name](player, game)
    return None # Pas de logique IA pour ce rôle ou ce joueur (humain)