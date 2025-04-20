# ai.py
import random

# Importez les classes nécessaires (assurez-vous que les chemins d'accès sont corrects)
# Assurez-vous que Player et Game sont importables si vous utilisez des types dans les signatures
try:
    from player import Player
    from game import Game
except ImportError:
    # Ceci permet au script ai.py de ne pas planter si exécuté seul,
    # mais il ne fonctionnera pas correctement sans les vraies classes.
    print("WARN: Player and Game classes not found. AI logic might not work correctly.")
    class Player: pass # Dummy class
    class Game: pass   # Dummy class


# Fonction utilitaire pour choisir une cible parmi une liste
def choose_target(potential_targets):
    if not potential_targets:
        return None
    return random.choice(potential_targets)

# --- Logiques IA par rôle ---

class AI_Logic:
    """
    Base class for all AI role logics.
    Each specific role AI should inherit from this class.
    """
    def __init__(self, player: Player, game: Game):
        self.player = player # The player instance this AI controls
        self.game = game     # Reference to the current game instance

    def decide_night_action(self, **kwargs):
        """
        Decide the action during the night.
        Should be overridden by specific roles with night actions.
        Returns None or a specific action/target based on the role.
        kwargs can contain context information (e.g., attaques_loups for Sorciere).
        """
        # Base class does nothing
        pass # Use 'pass' to indicate no action for roles without one

    def decide_vote(self):
         """
         Decide the action during the day (e.g., vote).
         Should be overridden by specific roles that vote.
         Returns a target player to vote for, or None for white vote.
         """
         # Base class does nothing, or could implement a default vote
         pass # Use 'pass' to indicate no specific voting logic

    def decide_chasseur_action(self):
        """
        Decide the target if this player is a dead Hunter.
        Should be overridden by the Hunter role AI.
        Returns a target player to eliminate, or None.
        """
        # Base class does nothing
        pass # Use 'pass'

    # You can add other base methods here if needed for more complex AI behaviors

class AI_Villageois(AI_Logic):
    def decide_night_action(self, **kwargs):
        # Villageois has no night action
        pass # Use 'pass'

    def decide_vote(self):
        # Vote aléatoirement pour un joueur vivant qui n'est pas soi-même
        alive_players = self.game.get_alive_players()
        potential_targets = [p for p in alive_players if p != self.player]
        # Ajouter une petite chance de voter blanc
        if random.random() < 0.05: # 5% de chance de voter blanc
             print(f"DEBUG IA Villageois {self.player.name}: Vote blanc.")
             return None
        target = choose_target(potential_targets)
        if target:
             print(f"DEBUG IA Villageois {self.player.name}: Vote pour {target.name}")
        else:
             print(f"DEBUG IA Villageois {self.player.name}: Pas de cible de vote possible (vote blanc).")
        return target # Retourne le joueur cible ou None

    def decide_chasseur_action(self):
        # Villageois can't be a Hunter, so this shouldn't be called.
        pass # Use 'pass'


class AI_LoupGarou(AI_Logic):
    def decide_night_action(self, **kwargs):
        # Les loups IA se "coordontent" pour choisir une cible aléatoire non-loup
        # Note : Cette IA simple ne gère pas la coordination réelle entre plusieurs loups IA.
        # Elle choisit simplement une cible pour le groupe.
        alive_players = self.game.get_alive_players()
        non_wolves = [p for p in alive_players if p.role and not p.role.is_wolf] # S'assurer que p.role existe
        target = choose_target(non_wolves)
        if target:
             print(f"DEBUG IA Loup-Garou {self.player.name}: Propose d'attaquer {target.name}")
        else:
             print(f"DEBUG IA Loup-Garou {self.player.name}: Pas de cible non-loup vivante possible (attaque annulée).")
        return target # Retourne le joueur cible ou None

    def decide_vote(self):
        # Vote aléatoirement pour un joueur vivant qui n'est PAS un loup (pour éviter de lycher un allié)
        alive_players = self.game.get_alive_players()
        non_wolves_alive = [p for p in alive_players if p.role and not p.role.is_wolf] # S'assurer que p.role existe
        target = choose_target(non_wolves_alive)
        if target:
            print(f"DEBUG IA Loup-Garou {self.player.name}: Vote pour {target.name} (anti-villageois)")
        else:
            # Si reste que des loups, vote pour soi-même ou blanc (règle peut varier)
            potential_targets = [p for p in alive_players if p != self.player] # Voter pour un autre loup ou blanc
            target = choose_target(potential_targets)
            if target:
                 print(f"DEBUG IA Loup-Garou {self.player.name}: Vote pour {target.name} (interne ou blanc)")
            else:
                 print(f"DEBUG IA Loup-Garou {self.player.name}: Pas de cible de vote possible (vote blanc).")

        return target # Retourne le joueur cible ou None

    def decide_chasseur_action(self):
        # Loup-Garou can't be a Hunter, so this shouldn't be called.
        pass # Use 'pass'


class AI_Voyante(AI_Logic):
     def __init__(self, player, game):
         super().__init__(player, game)
         self._last_seen_role = None # Stocke le rôle du joueur vu la nuit dernière
         self._last_seen_player = None # Stocke le joueur vu la nuit dernière

     def decide_night_action(self, **kwargs):
         # Espionne un joueur vivant aléatoirement (qui n'est pas soi-même)
         alive_players = self.game.get_alive_players()
         # Éviter d'espionner soi-même
         potential_targets = [p for p in alive_players if p != self.player]
         # Optionnel : Éviter d'espionner la même personne plusieurs fois si possible
         if self._last_seen_player and self._last_seen_player in potential_targets and len(potential_targets) > 1:
              potential_targets.remove(self._last_seen_player)

         target = choose_target(potential_targets)

         if target and target.role: # S'assurer qu'une cible a été choisie et a un rôle
             print(f"DEBUG (IA Voyante {self.player.name}) a vu le rôle de {target.name}: {target.role.name}")
             # L'IA stocke l'information pour le jour
             self._last_seen_role = target.role
             self._last_seen_player = target
         else:
             print(f"DEBUG (IA Voyante {self.player.name}): Pas de cible à espionner ou cible sans rôle.")
             self._last_seen_role = None
             self._last_seen_player = None

         # La Voyante IA retourne la cible espionnée pour que le jeu principal puisse l'afficher si besoin
         # Le jeu principal n'a pas besoin de cette information pour la logique de base, mais c'est une bonne pratique.
         return target

     def decide_vote(self):
         # Priorité : si a vu un loup et qu'il est vivant, vote pour lui. Sinon, vote aléatoirement.
         alive_players = self.game.get_alive_players()
         suspected_wolf = None

         # Vérifie si le joueur vu la nuit dernière était un loup et est toujours vivant
         if self._last_seen_role and self._last_seen_role.is_wolf and self._last_seen_player and self._last_seen_player.is_alive:
             suspected_wolf = self._last_seen_player

         if suspected_wolf and suspected_wolf != self.player: # S'assurer que ce n'est pas soi-même
             print(f"DEBUG (IA Voyante {self.player.name}) vote pour le loup identifié: {suspected_wolf.name}")
             return suspected_wolf
         else:
             # Si pas de loup identifié, loup identifié mort, ou loup identifié est soi-même (impossible si les rôles sont bien distribués), vote aléatoirement
             potential_targets = [p for p in alive_players if p != self.player]
             target = choose_target(potential_targets)
             if target:
                  print(f"DEBUG (IA Voyante {self.player.name}) vote pour {target.name} (aléatoire)")
             else:
                  print(f"DEBUG (IA Voyante {self.player.name}): Pas de cible de vote possible (vote blanc).")
             return target

     def decide_chasseur_action(self):
        # Voyante can't be a Hunter, so this shouldn't be called.
        pass # Use 'pass'


class AI_Sorciere(AI_Logic):
     # Accepte l'argument attaques_loups = le joueur attaqué par les loups (ou None)
     def decide_night_action(self, attaques_loups=None, **kwargs):
         """
         Sorciere decides whether to use potions.
         attaques_loups: The player attacked by the wolves this night (or None).
         Returns a dictionary {"save": Player or None, "kill": Player or None}.
         """
         action = {"save": None, "kill": None}
         print(f"DEBUG IA Sorcière {self.player.name}: Nuit. Attaqué = {attaques_loups.name if attaques_loups else 'Personne'}. Potions: Vie={self.player.has_saved_potion}, Mort={self.player.has_kill_potion}")

         # --- Décision de sauver ---
         # Si j'ai la potion de vie ET quelqu'un a été attaqué par les loups ET il est vivant ET ce n'est pas moi
         # Note : certaines règles permettent à la sorcière de se sauver elle-même. Si c'est le cas, enlevez le `attaques_loups != self.player`.
         if self.player.has_saved_potion and attaques_loups and attaques_loups.is_alive and attaques_loups != self.player:
             # Logique simple : 50% de chance de sauver la cible des loups si elle n'est pas elle-même
             # Logique alternative : 100% de chance de sauver si c'est un villageois connu / faible, 0% si loup connu (nécessite plus d'info IA)
             if random.random() < 0.5: # 50% chance de sauver
                  action["save"] = attaques_loups
                  print(f"DEBUG IA Sorcière {self.player.name}: Décide de sauver {attaques_loups.name}")
             else:
                  print(f"DEBUG IA Sorcière {self.player.name}: Ne sauve pas {attaques_loups.name} (décision IA).")


         # --- Décision de tuer ---
         # Si j'ai la potion de mort
         if self.player.has_kill_potion:
             # Logique simple : 30% de chance de tuer quelqu'un aléatoirement
             # Peut-être cibler un loup connu si la voyante a partagé (nécessite coordination IA ou info globale)
             # Peut-être cibler la cible des loups si je ne l'ai pas sauvée et que je veux qu'elle meure
             # Peut-être cibler quelqu'un d'autre que la cible des loups
             chance_de_tuer = 0.3 # 30% de chance de tuer

             if random.random() < chance_de_tuer:
                 alive_players = self.game.get_alive_players()
                 # Cibles potentielles pour tuer : tous les vivants SAUF soi-même, et SAUF la cible sauvée (si quelqu'un a été sauvé ce tour)
                 # Note : Les règles varient. Parfois, on peut tuer la cible des loups si on ne l'a pas sauvée.
                 # Ici, on exclut la cible *potentiellement* sauvée dans cette même nuit.
                 cibles_potentielles_kill = [
                      p for p in alive_players
                      if p != self.player and (action["save"] is None or p != action["save"])
                 ]
                 # Optionnel : exclure la cible des loups si elle n'a PAS été sauvée mais l'IA ne veut pas l'aider
                 # if attaques_loups and attaques_loups in cibles_potentielles_kill:
                 #    cibles_potentielles_kill.remove(attaques_loups) # Pour ne jamais tuer la cible des loups

                 target_to_kill = choose_target(cibles_potentielles_kill)

                 if target_to_kill:
                     action["kill"] = target_to_kill
                     print(f"DEBUG IA Sorcière {self.player.name}: Décide de tuer {target_to_kill.name}")
                 else:
                     print(f"DEBUG IA Sorcière {self.player.name}: Pas de cible valide à tuer.")
             else:
                  print(f"DEBUG IA Sorcière {self.player.name}: Ne tue personne (décision IA).")


         # Le jeu principal est responsable de marquer les potions comme utilisées APRÈS que l'IA ait retourné sa décision
         return action # Retourne un dictionnaire {"save": player_to_save, "kill": player_to_kill}

     def decide_vote(self):
         # Vote aléatoirement pour un joueur vivant
         alive_players = self.game.get_alive_players()
         potential_targets = [p for p in alive_players if p != self.player]
         # Ajouter une petite chance de voter blanc
         if random.random() < 0.05: # 5% de chance de voter blanc
             print(f"DEBUG IA Sorcière {self.player.name}: Vote blanc.")
             return None
         target = choose_target(potential_targets)
         if target:
              print(f"DEBUG IA Sorcière {self.player.name}: Vote pour {target.name}")
         else:
              print(f"DEBUG IA Sorcière {self.player.name}: Pas de cible de vote possible (vote blanc).")
         return target

     def decide_chasseur_action(self):
        # Sorciere can't be a Hunter, so this shouldn't be called.
        pass # Use 'pass'


class AI_Chasseur(AI_Logic):
    # Le chasseur IA n'a pas d'action de nuit ou de vote particulière quand il est vivant
    def decide_night_action(self, **kwargs):
        pass # Use 'pass'

    def decide_vote(self):
        pass # Use 'pass' (ou implémenter un vote aléatoire simple si désiré)
        # Exemple vote aléatoire simple si on veut qu'ils votent quand même:
        # alive_players = self.game.get_alive_players()
        # potential_targets = [p for p in alive_players if p != self.player]
        # target = choose_target(potential_targets)
        # if target: print(f"DEBUG IA Chasseur {self.player.name}: Vote pour {target.name}")
        # else: print(f"DEBUG IA Chasseur {self.player.name}: Vote blanc.")
        # return target


    # Son pouvoir s'active quand il meurt. Cette méthode est appelée par le jeu principal.
    def decide_chasseur_action(self):
        """Chasseur decides who to eliminate upon death."""
        print(f"DEBUG IA Chasseur {self.player.name} (mort) doit choisir une cible.")
        alive_players = self.game.get_alive_players()
        # Cannot target self (already dead)
        # Possible targets are all other living players
        potential_targets = [p for p in alive_players if p != self.player]

        target = choose_target(potential_targets)
        if target:
            print(f"DEBUG IA Chasseur {self.player.name} (mort): Tire sur {target.name}")
        else:
            print(f"DEBUG IA Chasseur {self.player.name} (mort): Pas de cible vivante à tirer.")
        return target # Retourne le joueur cible ou None

# Mapping des rôles aux logiques IA
AI_MAPPING = {
    "Villageois": AI_Villageois,
    "Loup-Garou": AI_LoupGarou,
    "Voyante": AI_Voyante,
    "Sorcière": AI_Sorciere,
    "Chasseur": AI_Chasseur
    # Ajoutez d'autres rôles ici si vous créez leur logique IA
}

# Fonction pour créer l'objet IA pour un joueur
def create_ai_logic(player: Player, game: Game):
    """
    Factory function to create the appropriate AI logic instance for a player.
    Args:
        player: The Player instance (must have role assigned).
        game: The Game instance.
    Returns:
        An instance of the specific role's AI logic (inheriting from AI_Logic),
        or None if the player is human or has no role,
        or a Base AI_Logic instance if no specific AI exists for the role.
    """
    # Do not create AI for human players or players without a role yet
    if not player or player.is_human or not player.role:
        # print(f"DEBUG AI: Not creating AI for player {player.name if player else 'None'} (is_human={player.is_human if player else 'N/A'}, role={player.role.name if player and player.role else 'None'}).")
        return None

    role_name = player.role.name
    ai_class = AI_MAPPING.get(role_name)

    if ai_class:
        print(f"DEBUG AI: Creating {ai_class.__name__} logic for {player.name} ({role_name})")
        return ai_class(player, game)
    else:
        print(f"WARN AI: No specific AI logic found for role: {role_name}. Using base AI.")
        # Return a base AI logic if no specific one is defined for this role
        return AI_Logic(player, game)


# Example of how to use this factory (for testing purposes, not part of main script)
if __name__ == '__main__':
    print("AI module loaded. Cannot run directly without Game/Player context.")
    # To test, you would need to create dummy Game and Player objects and pass them
    # to the create_ai_logic function.
    # Example:
    # class DummyGame:
    #      def __init__(self):
    #          self.players = []
    #      def get_alive_players(self):
    #          return [p for p in self.players if p.is_alive]
    #      # Add other methods mocked as needed by the AI logic (e.g., get_player_by_name)
    #
    # class DummyRole:
    #     def __init__(self, name, is_wolf=False):
    #         self.name = name
    #         self.is_wolf = is_wolf
    #
    # class DummyPlayer:
    #      def __init__(self, name, role_name, is_human=False, is_alive=True):
    #          self.name = name
    #          self.role = DummyRole(role_name, is_wolf=(role_name=="Loup-Garou"))
    #          self.is_human = is_human
    #          self.is_alive = is_alive
    #          self.has_saved_potion = (role_name=="Sorcière") # Start with potions if Sorciere
    #          self.has_kill_potion = (role_name=="Sorcière")
    #          # Add other attributes mocked as needed (e.g., is_attacked_this_night)
    #
    # # Setup a dummy game state for testing
    # game = DummyGame()
    # p_sorciere = DummyPlayer("IA_Sorciere", "Sorcière")
    # p_loup_attaq = DummyPlayer("AttackedPlayer", "Villageois")
    # p_villageois = DummyPlayer("Villageois1", "Villageois")
    # p_loup = DummyPlayer("IA_Loup", "Loup-Garou")
    # p_chasseur_mort = DummyPlayer("IA_Chasseur_Mort", "Chasseur", is_alive=False)
    # game.players = [p_sorciere, p_loup_attaq, p_villageois, p_loup, p_chasseur_mort]
    #
    # # Mock the attacked player for the Sorciere test
    # attacked_by_wolves = p_loup_attaq # Simulate this player was attacked
    #
    # # Test Sorciere AI
    # sorciere_ai = create_ai_logic(p_sorciere, game)
    # if sorciere_ai:
    #      print("\n--- Testing Sorciere AI ---")
    #      sorciere_action = sorciere_ai.decide_night_action(attaques_loups=attacked_by_wolves)
    #      print(f"Sorciere Decision: Save={sorciere_action.get('save', None).name if sorciere_action.get('save') else 'None'}, Kill={sorciere_action.get('kill', None).name if sorciere_action.get('kill') else 'None'}")
    #      # In the real game, game.saved_this_night and game.potioned_to_death_this_night would be set here
    #      # And potions would be consumed: p_sorciere.has_saved_potion = False etc.
    #
    # # Test Chasseur AI
    # chasseur_ai = create_ai_logic(p_chasseur_mort, game)
    # if chasseur_ai:
    #      print("\n--- Testing Chasseur AI ---")
    #      chasseur_target = chasseur_ai.decide_chasseur_action()
    #      print(f"Chasseur Decision: Shoot={chasseur_target.name if chasseur_target else 'None'}")
    #      # In the real game, chasseur_target.die() would be called here
    #
    # # Test Vote AI (e.g., Villageois)
    # print("\n--- Testing Vote AI (Villageois) ---")
    # villageois_ai = create_ai_logic(p_villageois, game)
    # if villageois_ai:
    #      vote_target = villageois_ai.decide_vote()
    #      print(f"Villageois Vote Decision: {vote_target.name if vote_target else 'Blanc'}")