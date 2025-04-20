import tkinter as tk
from tkinter import messagebox, simpledialog
from game import Game                     # Importer la classe Game depuis game.py
from player import Player                 # Importer la classe Player depuis player.py
from roles import get_available_roles     # Importer la fonction depuis roles.py
# Importer la fonction pour créer l'IA (assurez-vous qu'elle existe dans ai.py)
from ai import create_ai_logic, AI_LoupGarou, AI_Villageois # Importer spécifiquement si besoin
import random
import time # Potentiellement utile pour de petites pauses visuelles

class GameGUI:
    """
    Interface graphique pour le jeu Loup Garou Hybride.
    Gère l'affichage, l'input utilisateur, et le séquencement des phases de jeu
    en interaction avec l'objet Game et les logiques IA.
    """
    def __init__(self, master):
        self.master = master
        master.title("Loup Garou Hybride")
        master.geometry("600x650") # Définir une taille initiale raisonnable

        self.game = None # L'objet Game sera créé lors de la configuration
        self.current_human_actor = None # Le joueur humain qui doit agir
        self.pending_action_type = None # Type d'action attendue (ex: "vote", "Loup-Garou", etc.)
        self.possible_targets = [] # Liste des objets Player sélectionnables pour l'action en cours
        self._selected_target_for_human_action = None # Stocke temporairement la cible cliquée par l'humain
        self._human_vote_target = None # Stocke temporairement le joueur voté par l'humain
        self._human_vote_target_actor_name = None # Stocke le nom de l'acteur pour le retrouver

        # Variables pour gérer la séquence de vote
        self.voters_to_process = [] # Liste des joueurs qui doivent encore voter ce jour
        self.current_votes = {}     # Dictionnaire pour stocker les votes du jour {joueur_voté: nombre_de_votes}

        # Variables pour gérer la reprise de séquence après action humaine/popup
        self._remaining_night_roles_after_human = []
        self._hunter_revenge_next_phase_callback = None


        # --- Widgets ---

        # Frame pour la configuration (cachée au début)
        self.config_frame = tk.Frame(master)
        self.setup_config_frame() # Méthode pour créer les widgets de config

        # Frame pour le jeu (cachée au début)
        self.game_frame = tk.Frame(master)
        self.setup_game_frame() # Méthode pour créer les widgets du jeu

        # Afficher la frame de configuration au démarrage
        self.show_frame(self.config_frame)
        self.log_message("Bienvenue dans Loup Garou Hybride !") # Log initial dans config

    def setup_config_frame(self):
        """Crée les widgets pour l'écran de configuration."""
        frame = self.config_frame
        tk.Label(frame, text="Configuration de la Partie", font=("Arial", 16)).pack(pady=10)

        # Nombre total de joueurs
        tk.Label(frame, text="Nombre total de joueurs (min 4) :").pack()
        self.total_players_entry = tk.Entry(frame)
        self.total_players_entry.insert(0, "5") # Valeur par défaut
        self.total_players_entry.pack()

        # Nombre de joueurs humains
        tk.Label(frame, text="Nombre de joueurs humains :").pack()
        self.num_humans_entry = tk.Entry(frame)
        self.num_humans_entry.insert(0, "1") # Valeur par défaut
        self.num_humans_entry.pack()

        # Configuration des rôles (simplifié : liste de rôles et un bouton "Ajouter")
        tk.Label(frame, text="Rôles spéciaux à inclure (Sélection multiple possible) :\n(Loup-Garou et Villageois sont ajoutés si nécessaire)").pack(pady=5)
        # Utiliser un frame pour la listbox et sa scrollbar
        roles_list_frame = tk.Frame(frame)
        roles_list_frame.pack(pady=5)
        roles_scrollbar = tk.Scrollbar(roles_list_frame)
        roles_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.roles_listbox = tk.Listbox(roles_list_frame, selectmode=tk.MULTIPLE, height=min(len(get_available_roles()), 8), yscrollcommand=roles_scrollbar.set)
        available_roles = get_available_roles()
        # Exclure Loup-Garou et Villageois de la sélection explicite pour simplifier la config auto
        roles_for_selection = [r for r in available_roles if r not in ["Loup-Garou", "Villageois"]]
        for role in roles_for_selection:
             self.roles_listbox.insert(tk.END, role)
        self.roles_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        roles_scrollbar.config(command=self.roles_listbox.yview)

        # Zone de message pour la configuration (pour log_message)
        self.config_message_area = tk.Text(frame, height=4, width=60, state=tk.DISABLED, wrap=tk.WORD)
        self.config_message_area.pack(pady=10)

        # Bouton pour démarrer la partie
        tk.Button(frame, text="Démarrer la Partie", command=self.start_game).pack(pady=20)

    def setup_game_frame(self):
        """Crée les widgets pour l'écran de jeu."""
        frame = self.game_frame

        # Zone pour les messages du jeu
        self.message_area = tk.Text(frame, height=18, width=70, state=tk.DISABLED, wrap=tk.WORD) # wrap=tk.WORD pour éviter les coupures de mots
        self.message_area.pack(pady=10, padx=10)

        # --- Frame pour les infos joueurs et actions ---
        bottom_frame = tk.Frame(frame)
        bottom_frame.pack(fill=tk.X, padx=10)

        # --- Frame gauche pour la liste des joueurs ---
        player_list_outer_frame = tk.Frame(bottom_frame)
        player_list_outer_frame.pack(side=tk.LEFT, padx=5, fill=tk.Y)

        tk.Label(player_list_outer_frame, text="Joueurs :").pack()
        # Utiliser un frame pour la listbox et sa scrollbar
        player_list_frame = tk.Frame(player_list_outer_frame)
        player_list_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(player_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.players_listbox = tk.Listbox(player_list_frame, height=12, width=30, yscrollcommand=scrollbar.set)
        self.players_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.players_listbox.yview)

        self.players_listbox.bind('<<ListboxSelect>>', self.on_player_select) # Gérer la sélection

        # --- Frame droite pour les boutons d'action et le rôle ---
        self.action_info_frame = tk.Frame(bottom_frame) # <-- Utiliser self.
        self.action_info_frame.pack(side=tk.LEFT, padx=10, fill=tk.Y, expand=True, anchor=tk.N)

        # Afficher le rôle du joueur humain actuel (sih un seul humain joue)
        self.human_role_label = tk.Label(self.action_info_frame, text="", font=("Arial", 12, "bold"), justify=tk.LEFT)
        self.human_role_label.pack(pady=5, anchor=tk.W)

        # Label pour indiquer l'action en cours
        self.action_prompt_label = tk.Label(self.action_info_frame, text="", justify=tk.LEFT)
        self.action_prompt_label.pack(pady=5, anchor=tk.W)


        # Boutons pour les actions humaines (visibilité gérée dynamiquement)
        self.action_buttons_frame = tk.Frame(self.action_info_frame)
        self.action_buttons_frame.pack(pady=10, anchor=tk.W) # Aligner à gauche

        self.confirm_action_button = tk.Button(self.action_buttons_frame, text="Confirmer Action", state=tk.DISABLED, command=self.confirm_human_action)
        self.confirm_action_button.pack(side=tk.LEFT, padx=5)

        # Le bouton "Passer" est activé seulement si l'action le permet (ex: Voyante)
        self.pass_action_button = tk.Button(self.action_buttons_frame, text="Passer l'action", state=tk.DISABLED, command=self.pass_human_action)
        self.pass_action_button.pack(side=tk.LEFT, padx=5)

    def log_message(self, message):
        """Ajoute un message à la zone de texte appropriée (config ou jeu)."""
        if self.config_frame.winfo_ismapped(): # Si la frame config est visible
            area = self.config_message_area
        elif self.game_frame.winfo_ismapped(): # Si la frame jeu est visible
            area = self.message_area
        else:
            return # Ne rien faire si aucune frame n'est visible (ne devrait pas arriver)

        area.config(state=tk.NORMAL)
        area.insert(tk.END, message + "\n")
        area.see(tk.END) # Scroll to the bottom
        area.config(state=tk.DISABLED)
        self.master.update_idletasks() # Forcer la mise à jour de l'UI pour voir les messages

    def show_frame(self, frame_to_show):
        """Affiche la frame spécifiée et cache les autres."""
        if hasattr(self, 'config_frame'): self.config_frame.pack_forget()
        if hasattr(self, 'game_frame'): self.game_frame.pack_forget()
        frame_to_show.pack(fill=tk.BOTH, expand=True)

    def update_player_list_display(self):
        """Met à jour la listbox des joueurs avec leur statut (vivant/mort)."""
        self.players_listbox.delete(0, tk.END)
        if self.game:
            alive_count = 0
            for index, player in enumerate(self.game.players):
                status = "Vivant" if player.is_alive else "Mort"
                display_text = f"{player.name} ({status})"
                self.players_listbox.insert(tk.END, display_text)
                if not player.is_alive:
                    # Colorer les morts en rouge (optionnel)
                    self.players_listbox.itemconfig(index, {'fg': 'red'})
                else:
                    alive_count += 1
            # Optionnel: mettre à jour un label avec le compte des vivants
            # self.alive_count_label.config(text=f"Joueurs vivants: {alive_count}")

    def get_selected_player_from_listbox(self):
        """Récupère l'objet Player correspondant à la sélection actuelle dans la listbox."""
        selected_indices = self.players_listbox.curselection()
        if selected_indices:
            selected_index = selected_indices[0]
            selected_player_display = self.players_listbox.get(selected_index)
            # Extraire le nom (tout avant la première parenthèse ouvrante, moins l'espace)
            try:
                 name_part = selected_player_display.split('(')[0].strip()
                 return self.game.get_player_by_name(name_part)
            except Exception:
                 print(f"Erreur: Impossible d'extraire le nom de '{selected_player_display}'")
                 return None
        return None

    def on_player_select(self, event):
        """Gère la sélection d'un joueur dans la listbox."""
        if self.current_human_actor and self.pending_action_type: # Si une action humaine est en attente
             selected_player = self.get_selected_player_from_listbox()
             if selected_player:
                  # Stocker le joueur sélectionné temporairement
                  self._selected_target_for_human_action = selected_player
                  # Activer le bouton de confirmation si la cible est dans les cibles possibles
                  if selected_player in self.possible_targets:
                      self.confirm_action_button.config(state=tk.NORMAL)
                      print(f"DEBUG: Cible {selected_player.name} valide sélectionnée pour {self.pending_action_type}.")
                  else:
                       self.confirm_action_button.config(state=tk.DISABLED) # Désactiver si cible invalide
                       print(f"DEBUG: Cible {selected_player.name} invalide pour {self.pending_action_type}.")
             else:
                  self._selected_target_for_human_action = None
                  self.confirm_action_button.config(state=tk.DISABLED)

    def start_game(self):
        """Démarre une nouvelle partie."""
        try:
            total_players = int(self.total_players_entry.get())
            num_humans = int(self.num_humans_entry.get())
            if total_players < 4:
                messagebox.showerror("Erreur de configuration", "Le nombre total de joueurs doit être d'au moins 4.")
                return
            if num_humans < 0 or num_humans > total_players:
                 messagebox.showerror("Erreur de configuration", f"Le nombre de joueurs humains doit être entre 0 et {total_players}.")
                 return

            num_ia = total_players - num_humans

            # Construire la configuration des rôles
            selected_indices = self.roles_listbox.curselection()
            selected_special_roles = [self.roles_listbox.get(i) for i in selected_indices]

            roles_config = {}
            # Ajouter les rôles spéciaux sélectionnés (1 de chaque)
            for role_name in selected_special_roles:
                 roles_config[role_name] = roles_config.get(role_name, 0) + 1

            # Assurer la présence d'au moins un Loup-Garou
            if "Loup-Garou" not in roles_config:
                 roles_config["Loup-Garou"] = 1

            # Remplir le reste avec des Villageois
            current_role_count = sum(roles_config.values())
            if current_role_count < total_players:
                 roles_config["Villageois"] = total_players - current_role_count
            elif current_role_count > total_players:
                 # Trop de rôles spéciaux sélectionnés + 1 Loup Garou ? Erreur config.
                 messagebox.showerror("Erreur de configuration", f"Trop de rôles ({current_role_count}) pour {total_players} joueurs. Désélectionnez des rôles spéciaux.")
                 return

            # Vérification finale (ex: s'assurer qu'il y a des villageois si des loups existent)
            if roles_config.get("Loup-Garou", 0) > 0 and roles_config.get("Villageois", 0) == 0 and total_players > roles_config.get("Loup-Garou"):
                messagebox.showerror("Erreur de configuration", "Configuration invalide : présence de Loup(s) sans aucun Villageois.")
                return

            self.log_message(f"Configuration validée: {roles_config}")
            print(f"DEBUG: Config de rôles calculée: {roles_config}") # Utile pour vérifier la distribution calculée

            # --- Création du jeu et des joueurs ---
            self.game = Game()
            # Créer les joueurs humains
            human_names = []
            for i in range(num_humans):
                name = simpledialog.askstring("Nom du joueur", f"Entrez le nom du joueur humain {i+1} :", parent=self.master)
                if not name or name.strip() == "": name = f"Humain_{i+1}"
                name = name.strip() # Enlever espaces début/fin
                # Vérifier si le nom existe déjà
                loop_guard = 0
                while name in human_names or name.lower().startswith("ia_") or self.game.get_player_by_name(name): # Vérifier aussi get_player_by_name
                     name = simpledialog.askstring("Nom du joueur", f"Nom '{name}' invalide ou déjà pris. Entrez un nom différent pour le joueur humain {i+1} :", parent=self.master)
                     if not name or name.strip() == "": name = f"Humain_{i+1}_{random.randint(100,999)}" # Générer un nom unique plus robuste
                     name = name.strip()
                     loop_guard += 1
                     if loop_guard > 10: # Sécurité anti-boucle
                         messagebox.showerror("Erreur", "Impossible de trouver un nom unique.")
                         return

                self.game.add_player(Player(name, is_human=True))
                human_names.append(name)

            # Créer les joueurs IA (Correction de la boucle)
            ia_index = 1
            num_ia_added = 0
            for _ in range(num_ia):
                player_added = False
                loop_guard = 0
                while not player_added:
                    name = f"IA_{ia_index}"
                    # Vérifier les conflits avec humains ET IA déjà ajoutés (via get_player_by_name)
                    if not self.game.get_player_by_name(name): # get_player_by_name est insensible à la casse
                        self.game.add_player(Player(name, is_human=False))
                        player_added = True
                        num_ia_added += 1
                    ia_index += 1
                    loop_guard += 1
                    if loop_guard > total_players * 2 + 10: # Sécurité anti-boucle infinie
                         messagebox.showerror("Erreur critique", "Impossible de générer des noms IA uniques.")
                         self.game = None
                         return

            self.log_message(f"{num_ia_added} joueurs IA ajoutés.")
            print(f"DEBUG: Ajouté {num_ia_added} joueurs IA.")

            # --- Fin création joueurs ---

            # Vérification finale du nombre total de joueurs
            if len(self.game.players) != total_players:
                 messagebox.showerror("Erreur interne", f"Incohérence: {len(self.game.players)} joueurs créés au lieu de {total_players}.")
                 self.game = None
                 return

            # --- Attribution des rôles et démarrage ---
            if self.game.assign_roles(roles_config):
                # Assigner les logiques IA après l'assignation des rôles
                for player in self.game.players:
                    if not player.is_human:
                        player.ai_logic = create_ai_logic(player, self.game) # Assigne l'objet logique AI au joueur IA

                # Nettoyer la zone de message de la config avant de changer
                self.config_message_area.config(state=tk.NORMAL)
                self.config_message_area.delete(1.0, tk.END)
                self.config_message_area.config(state=tk.DISABLED)

                # Changer l'affichage
                self.show_frame(self.game_frame)
                self.log_message("La partie commence !")
                self.log_message(f"Joueurs humains : {', '.join(human_names)}")
                self.log_message("Distribution des rôles...")

                # Afficher le rôle pour chaque joueur humain
                if num_humans == 1:
                     human_player = next((p for p in self.game.players if p.is_human), None)
                     if human_player:
                          self.human_role_label.config(text=f"Votre rôle : {human_player.role.name}")
                          self.log_message(f"Votre rôle est : {human_player.role.name}")
                elif num_humans > 1:
                    messagebox.showinfo("Rôles Distribués", "Les rôles vont être affichés pour chaque joueur humain.\nAssurez-vous que seul le joueur concerné regarde !", parent=self.master)
                    for player in self.game.players:
                         if player.is_human:
                             messagebox.showinfo(f"Rôle de {player.name}", f"{player.name}, votre rôle est : {player.role.name}", parent=self.master)

                self.update_player_list_display()
                # Démarrer la première phase, qui est la Nuit 1
                self.master.after(1500, self.start_night_phase) # Démarre la nuit après 1.5 seconde

            else:
                # assign_roles a échoué (message d'erreur déjà affiché par game.py)
                self.log_message("Erreur lors de l'assignation des rôles. Vérifiez la console ou la configuration.")
                self.game = None # Nettoyer

        except ValueError:
            messagebox.showerror("Erreur de saisie", "Veuillez entrer des nombres valides pour le nombre de joueurs.")
            self.log_message("Erreur de saisie dans la configuration.")
        except Exception as e:
            messagebox.showerror("Erreur inattendue", f"Une erreur est survenue lors du démarrage :\n {e}")
            self.log_message(f"Erreur inattendue: {e}")
            print(f"Erreur lors du démarrage: {e}") # Print pour le debug complet

    # ============================================
    # == GESTION DES PHASES DE JEU (Nuit/Jour) ==
    # ============================================

    def start_night_phase(self):
        """Initialise et gère la phase de nuit."""
        if not self.game or self.game.game_over: return

        self.game.is_day = False
        self.game.day_count += 1

        self.log_message(f"\n--- Nuit {self.game.day_count} ---")
        self.log_message("Le village s'endort...")
        self.action_prompt_label.config(text="Nuit...")

        # Réinitialiser les états temporaires de la nuit
        for player in self.game.players:
             player.is_attacked_this_night = False
        self.game.killed_this_night = []
        self.game.saved_this_night = None
        self.game.potioned_to_death_this_night = None
        self._remaining_night_roles_after_human = []

        # Lancer la séquence des actions de nuit
        night_roles_order = ["Loup-Garou", "Voyante", "Sorcière"]
        self.execute_night_actions_sequence(night_roles_order)

    def execute_night_actions_sequence(self, remaining_roles_order):
        """Exécute les actions de nuit rôle par rôle, gérant humains et IA."""
        if not self.game or self.game.game_over: return

        if not remaining_roles_order:
            print("DEBUG: Séquence d'actions de nuit terminée. Résolution...")
            self.master.after(500, self.resolve_night_gui)
            return

        current_role_name = remaining_roles_order[0]
        players_of_this_role = [p for p in self.game.get_alive_players() if p.role.name == current_role_name]

        if not players_of_this_role:
            print(f"DEBUG: Aucun joueur vivant pour le rôle '{current_role_name}'. Passe à la suite.")
            self.master.after(50, self.execute_night_actions_sequence, remaining_roles_order[1:])
            return

        self_as_human_actor = next((p for p in players_of_this_role if p.is_human), None)

        if self_as_human_actor:
            # Joueur humain pour ce rôle
            if current_role_name == "Sorcière" and (not self_as_human_actor.has_saved_potion and not self_as_human_actor.has_kill_potion):
                self.log_message(f"{self_as_human_actor.name} (Sorcière) n'a plus de potions et passe son tour.")
                self.master.after(500, self.execute_night_actions_sequence, remaining_roles_order[1:])
            elif current_role_name == "Chasseur":
                self.master.after(50, self.execute_night_actions_sequence, remaining_roles_order[1:])
            else:
                # Humain avec action (Loup, Voyante, Sorcière avec potions)
                if current_role_name == "Sorcière":
                    attacked_by_wolves = self.game.killed_this_night[0] if self.game.killed_this_night else None
                    self.sorciere_action_popup(self_as_human_actor, attacked_by_wolves, remaining_roles_order[1:])
                else:
                    self.prompt_human_night_action(self_as_human_actor, remaining_roles_order[1:])
                return # STOP, attend input humain

        else: # Que des joueurs IA pour ce rôle
             print(f"DEBUG: Joueurs IA pour le rôle '{current_role_name}' agissent...")
             # --- Logique IA ---
             if current_role_name == "Loup-Garou":
                  loup_ia_actor = players_of_this_role[0]
                  if hasattr(loup_ia_actor, 'ai_logic') and loup_ia_actor.ai_logic:
                       target = loup_ia_actor.ai_logic.decide_night_action()
                       if target and target.is_alive:
                            self.game.killed_this_night.append(target)
                            print(f"DEBUG: Loups-Garous IA ont choisi de dévorer {target.name}")
                       else: print("DEBUG: Loups-Garous IA n'ont pas trouvé de cible valide.")
                  else: print(f"ERREUR: Loup IA {loup_ia_actor.name} n'a pas d'ai_logic.")
             elif current_role_name == "Voyante":
                  for voyante_ia_actor in players_of_this_role:
                      if hasattr(voyante_ia_actor, 'ai_logic') and voyante_ia_actor.ai_logic:
                          voyante_ia_actor.ai_logic.decide_night_action()
                      else: print(f"ERREUR: Voyante IA {voyante_ia_actor.name} n'a pas d'ai_logic.")
             elif current_role_name == "Sorcière":
                  ia_witches_with_potions = [p for p in players_of_this_role if (p.has_saved_potion or p.has_kill_potion)]
                  for sorciere_ia_actor in ia_witches_with_potions:
                      if hasattr(sorciere_ia_actor, 'ai_logic') and sorciere_ia_actor.ai_logic:
                           # Informer l'IA Sorcière de l'attaque (Correction indentation ici)
                           attacked_by_wolves = self.game.killed_this_night[0] if self.game.killed_this_night else None
                           if attacked_by_wolves:
                               attacked_by_wolves.is_attacked_this_night = True
                           else:
                               # Reset flag for all players if no wolf attack
                               for p in self.game.players:
                                   p.is_attacked_this_night = False
                           action = sorciere_ia_actor.ai_logic.decide_night_action() # L'IA décide APRES avoir été informée

                           # Appliquer les décisions
                           if action["save"] and sorciere_ia_actor.has_saved_potion:
                               if action["save"].is_alive:
                                   self.game.saved_this_night = action["save"]
                                   sorciere_ia_actor.has_saved_potion = False
                                   print(f"DEBUG: Sorcière IA {sorciere_ia_actor.name} utilise vie sur {self.game.saved_this_night.name}.")
                               else: print(f"DEBUG: Sorcière IA {sorciere_ia_actor.name} cible save morte.")
                           if action["kill"] and sorciere_ia_actor.has_kill_potion and self.game.saved_this_night is None:
                               if action["kill"].is_alive:
                                   self.game.potioned_to_death_this_night = action["kill"]
                                   sorciere_ia_actor.has_kill_potion = False
                                   print(f"DEBUG: Sorcière IA {sorciere_ia_actor.name} utilise mort sur {self.game.potioned_to_death_this_night.name}.")
                               else: print(f"DEBUG: Sorcière IA {sorciere_ia_actor.name} cible kill morte.")
                      else: print(f"ERREUR: Sorcière IA {sorciere_ia_actor.name} n'a pas d'ai_logic.")
             # --- Fin Logique IA ---
             # Passer au rôle suivant
             self.master.after(500, self.execute_night_actions_sequence, remaining_roles_order[1:])

    def prompt_human_night_action(self, player, remaining_roles_after_this_one):
        """Prépare l'interface pour l'action d'un joueur humain la nuit (Loup, Voyante)."""
        role_name = player.role.name
        self.action_prompt_label.config(text=f"Tour de : {player.name} ({role_name})")

        self.current_human_actor = player
        self.pending_action_type = role_name
        self._remaining_night_roles_after_human = remaining_roles_after_this_one

        self.possible_targets = []
        prompt_text = ""
        can_pass = False

        if role_name == "Loup-Garou":
             self.possible_targets = [p for p in self.game.get_alive_players() if not p.role.is_wolf]
             prompt_text = "Qui voulez-vous dévorer ?"
             can_pass = False
        elif role_name == "Voyante":
             self.possible_targets = [p for p in self.game.get_alive_players() if p != player]
             prompt_text = "Qui voulez-vous espionner ?"
             can_pass = True

        self.log_message(f"\n{player.name} ({role_name}), c'est votre tour.")
        self.log_message(prompt_text)
        self.log_message("Sélectionnez un joueur dans la liste et Confirmez (ou Passez si disponible).")

        self.players_listbox.config(selectmode=tk.SINGLE)
        self.players_listbox.selection_clear(0, tk.END)
        self._selected_target_for_human_action = None
        self.confirm_action_button.config(state=tk.DISABLED)
        self.pass_action_button.config(state=tk.NORMAL if can_pass else tk.DISABLED)

    def sorciere_action_popup(self, sorciere_player, attacked_by_wolves, remaining_roles_after_witch):
        """Gère l'action de la sorcière humaine via un popup modale."""
        popup = tk.Toplevel(self.master)
        popup.title("Action de la Sorcière")
        popup.geometry("350x300")
        popup.transient(self.master)
        popup.grab_set()

        tk.Label(popup, text=f"{sorciere_player.name}, c'est votre tour.", font=("Arial", 12, "bold")).pack(pady=10)

        info_frame = tk.Frame(popup)
        info_frame.pack(pady=5)
        if attacked_by_wolves: tk.Label(info_frame, text=f"Attaque des loups : {attacked_by_wolves.name}").pack()
        else: tk.Label(info_frame, text="Aucune attaque des loups cette nuit.").pack()
        tk.Label(info_frame, text=f"Potions - Vie: {'Oui' if sorciere_player.has_saved_potion else 'Non'}, Mort: {'Oui' if sorciere_player.has_kill_potion else 'Non'}").pack()

        action_frame = tk.Frame(popup)
        action_frame.pack(pady=10)

        tk.Label(action_frame, text="Cible (si potion utilisée) :").pack()
        target_listbox = tk.Listbox(action_frame, height=5, width=25, selectmode=tk.SINGLE, exportselection=False)
        alive_players = self.game.get_alive_players()
        for p in alive_players: target_listbox.insert(tk.END, p.name)
        target_listbox.pack()

        save_choice = tk.BooleanVar(value=False)
        kill_choice = tk.BooleanVar(value=False)
        selected_target_name = None

        def on_select(event):
            indices = target_listbox.curselection()
            if indices: nonlocal selected_target_name; selected_target_name = target_listbox.get(indices[0])

        target_listbox.bind('<<ListboxSelect>>', on_select)

        button_frame = tk.Frame(popup)
        button_frame.pack(pady=10)

        if sorciere_player.has_saved_potion: tk.Checkbutton(button_frame, text="Utiliser Potion Vie", variable=save_choice).pack(anchor=tk.W)
        if sorciere_player.has_kill_potion: tk.Checkbutton(button_frame, text="Utiliser Potion Mort", variable=kill_choice).pack(anchor=tk.W)

        def confirm():
            save_potion_used = save_choice.get()
            kill_potion_used = kill_choice.get()
            target = self.game.get_player_by_name(selected_target_name) if selected_target_name else None

            # Validation
            if (save_potion_used or kill_potion_used) and not target: messagebox.showwarning("Action Invalide", "Veuillez sélectionner une cible si vous utilisez une potion.", parent=popup); return
            if save_potion_used and kill_potion_used: messagebox.showwarning("Action Invalide", "Une seule potion par nuit.", parent=popup); return
            if kill_potion_used and target == sorciere_player: messagebox.showwarning("Action Invalide", "Impossible de s'auto-empoisonner.", parent=popup); return
            if target and not target.is_alive: messagebox.showwarning("Action Invalide", "Cible déjà morte.", parent=popup); return

            # Appliquer actions
            if save_potion_used:
                 self.game.saved_this_night = target
                 sorciere_player.has_saved_potion = False
                 self.log_message(f"La Sorcière {sorciere_player.name} utilise Potion Vie sur {target.name}.")
                 print(f"DEBUG: Sorcière humaine {sorciere_player.name} use vie sur {target.name}.")
            if kill_potion_used:
                 self.game.potioned_to_death_this_night = target
                 sorciere_player.has_kill_potion = False
                 self.log_message(f"La Sorcière {sorciere_player.name} utilise Potion Mort sur {target.name}.")
                 print(f"DEBUG: Sorcière humaine {sorciere_player.name} use mort sur {target.name}.")

            popup.destroy()
            self.current_human_actor = None; self.pending_action_type = None # Humain a fini
            self.master.after(100, self.execute_night_actions_sequence, remaining_roles_after_witch) # Reprend la séquence

        def pass_turn():
             popup.destroy()
             self.current_human_actor = None; self.pending_action_type = None # Humain a fini
             self.master.after(100, self.execute_night_actions_sequence, remaining_roles_after_witch) # Reprend la séquence

        tk.Button(popup, text="Confirmer", command=confirm).pack(side=tk.LEFT, padx=5, pady=10)
        tk.Button(popup, text="Passer mon tour", command=pass_turn).pack(side=tk.LEFT, padx=5, pady=10)

        self.master.wait_window(popup)

    def resolve_night_gui(self):
        """Résout les actions de la nuit et applique les morts."""
        if not self.game or self.game.game_over: return
        self.action_prompt_label.config(text="Résolution de la nuit...")

        self.log_message("\nLe village se réveille...")

        killed_players_this_night_actual = []

        # Résolution Loups
        attacked_by_wolves = self.game.killed_this_night[0] if self.game.killed_this_night else None
        if attacked_by_wolves and attacked_by_wolves.is_alive and attacked_by_wolves != self.game.saved_this_night:
            killed_players_this_night_actual.append(attacked_by_wolves)
            self.log_message(f"{attacked_by_wolves.name} a été dévoré(e) par les Loups-Garous.")

        # Résolution Sorcière (mort)
        potioned_to_death = self.game.potioned_to_death_this_night
        if potioned_to_death and potioned_to_death.is_alive and potioned_to_death != self.game.saved_this_night and potioned_to_death not in killed_players_this_night_actual:
             killed_players_this_night_actual.append(potioned_to_death)
             self.log_message(f"{potioned_to_death.name} a été empoisonné(e) par la Sorcière.")

        # Appliquer les morts
        players_who_just_died_this_phase = []
        for player_to_die in killed_players_this_night_actual:
            if player_to_die.is_alive:
                 player_to_die.die()
                 players_who_just_died_this_phase.append(player_to_die)

        self.update_player_list_display()

        # Gérer Chasseur(s) mort(s)
        hunters_who_just_died = [p for p in players_who_just_died_this_phase if p.role.name == "Chasseur"]
        if hunters_who_just_died:
             self.handle_hunter_sequence(hunters_who_just_died, self.check_victory_and_start_day_phase)
        else:
             self.master.after(1000, self.check_victory_and_start_day_phase)

    def handle_hunter_sequence(self, hunters_list, callback_after_hunters_done):
        """Gère le pouvoir des Chasseurs morts, un par un."""
        if not self.game or self.game.game_over:
            # Si la partie s'est terminée pendant la séquence (ex: chasseur tue dernier loup)
            self.check_victory_and_proceed(callback_after_hunters_done)
            return

        if not hunters_list:
            print("DEBUG: Séquence chasseur terminée. Appel du callback.")
            self.check_victory_and_proceed(callback_after_hunters_done)
            return

        hunter_player = hunters_list.pop(0)

        # Vérifier si le chasseur est toujours "logiquement" autorisé à agir (n'a pas été tué par un autre chasseur avant son tour)
        # Ici on vérifie juste s'il est vivant *maintenant* ce qui est incorrect. Il faut un drapeau pour savoir s'il a déjà agi.
        # Simplification V1: On assume qu'il peut agir si listé, mais on vérifie si la cible est vivante.
        if not hunter_player.is_alive: # Il est censé être mort logiquement
             pass # OK
        else:
             # Cas étrange, il devrait être mort. On log et on skip.
             print(f"AVERTISSEMENT: Chasseur {hunter_player.name} listé pour agir mais trouvé vivant.")
             self.master.after(50, self.handle_hunter_sequence, hunters_list, callback_after_hunters_done)
             return


        self.log_message(f"\nLe Chasseur {hunter_player.name} est mort et doit éliminer quelqu'un !")
        self.action_prompt_label.config(text=f"Tour de : Chasseur {hunter_player.name} (mort)")

        alive_players_for_hunter = self.game.get_alive_players()
        if not alive_players_for_hunter:
            self.log_message(f"Le Chasseur {hunter_player.name} meurt, mais il n'y a plus personne à éliminer.")
            self.master.after(100, self.handle_hunter_sequence, hunters_list, callback_after_hunters_done)
            return

        if hunter_player.is_human:
            self.current_human_actor = hunter_player
            self.pending_action_type = "hunter_revenge"
            self.possible_targets = alive_players_for_hunter
            # Le callback après l'action humaine est de continuer la séquence des chasseurs
            self._hunter_revenge_next_phase_callback = lambda: self.handle_hunter_sequence(hunters_list, callback_after_hunters_done)

            self.log_message("Qui voulez-vous éliminer en mourant ?")
            self.log_message("Sélectionnez un joueur et Confirmez.")
            self.players_listbox.config(selectmode=tk.SINGLE)
            self.players_listbox.selection_clear(0, tk.END)
            self._selected_target_for_human_action = None
            self.confirm_action_button.config(state=tk.DISABLED)
            self.pass_action_button.config(state=tk.DISABLED)
            # Attend l'input humain via confirm_human_action
            return # STOP

        else: # Chasseur IA
             print(f"DEBUG: Chasseur IA {hunter_player.name} agit...")
             hunter_target = random.choice(alive_players_for_hunter) if alive_players_for_hunter else None

             if hunter_target:
                  self.log_message(f"Le Chasseur IA {hunter_player.name} élimine {hunter_target.name} en mourant.")
                  target_was_already_dead = not hunter_target.is_alive
                  hunter_target.die()
                  if not target_was_already_dead and hunter_target.role.name == "Chasseur":
                      # Si le chasseur IA tue un autre chasseur qui n'était pas déjà mort, l'ajouter à la séquence
                      print(f"DEBUG: Chasseur IA a tué un autre chasseur ({hunter_target.name}), ajout à la liste.")
                      # Insérer au début pour qu'il agisse ensuite ? Ou à la fin ? Début semble logique.
                      hunters_list.insert(0, hunter_target)
                  self.update_player_list_display()
             else:
                  self.log_message("Le Chasseur IA n'a pas trouvé de cible valide.")

             # Après l'action IA du Chasseur, passer au chasseur suivant ou terminer
             self.master.after(1000, self.handle_hunter_sequence, hunters_list, callback_after_hunters_done)

    def check_victory_and_proceed(self, next_phase_callback):
         """Vérifie victoire et appelle le callback si jeu continue."""
         self.update_player_list_display()
         if self.game.check_victory_condition():
              self.end_game_gui()
         else:
              self.master.after(100, next_phase_callback)

    def check_victory_and_start_day_phase(self):
        """Vérifie victoire après nuit/chasseur et lance le jour."""
        self.check_victory_and_proceed(self.start_day_phase)

    def start_day_phase(self):
        """Initialise et gère la phase de jour (débat et vote)."""
        if not self.game or self.game.game_over: return

        self.game.is_day = True
        self.action_prompt_label.config(text="Jour - Débat / Vote")

        self.log_message(f"\n--- Jour {self.game.day_count} ---")

        alive_players = self.game.get_alive_players()
        self.log_message(f"Joueurs vivants : {', '.join([p.name for p in alive_players])}")

        # Vérifier victoire en début de journée
        if self.game.check_victory_condition():
             self.end_game_gui()
             return

        # Phase de Débat
        human_players_alive = [p for p in alive_players if p.is_human]
        if len(human_players_alive) > 1:
             self.log_message("\nPhase de débat. Joueurs humains, discutez entre vous.")
             # Ajouter un bouton "Passer au Vote"
             if not hasattr(self, '_pass_vote_button') or not self._pass_vote_button.winfo_exists():
                 self._pass_vote_button = tk.Button(self.action_info_frame, text="Passer au Vote", command=self.start_vote_phase)
                 self._pass_vote_button.pack(pady=10)
        else:
             self.master.after(1500, self.start_vote_phase)

    def start_vote_phase(self):
        """Lance la phase de vote."""
        if not self.game or self.game.game_over: return
        # Supprimer le bouton "Passer au Vote"
        if hasattr(self, '_pass_vote_button') and self._pass_vote_button.winfo_exists():
             self._pass_vote_button.destroy()

        self.log_message("\n--- Phase de Vote ---")
        self.action_prompt_label.config(text="Vote en cours...")
        self.update_player_list_display()

        alive_players = self.game.get_alive_players()
        self.voters_to_process = list(alive_players)
        self.current_votes = {}
        self._human_vote_target = None
        self._human_vote_target_actor_name = None

        self.process_next_voter() # Lance la séquence

    def process_next_voter(self):
        """Traite le prochain joueur dans la file d'attente de vote."""
        if not self.game or self.game.game_over: return

        # --- Traitement du vote humain précédent ---
        if self._human_vote_target is not None:
             voter_who_just_voted = self.game.get_player_by_name(self._human_vote_target_actor_name) if self._human_vote_target_actor_name else None
             if voter_who_just_voted and self._human_vote_target.is_alive: # S'assurer que la cible est tjrs vivante
                  target = self._human_vote_target
                  self.current_votes[target] = self.current_votes.get(target, 0) + 1
                  # Log vote ici pour être sûr qu'il est compté
                  self.log_message(f"{voter_who_just_voted.name} a voté pour {target.name}.")
                  print(f"DEBUG: Vote humain de {voter_who_just_voted.name} pour {target.name} enregistré.")
             elif voter_who_just_voted:
                  self.log_message(f"{voter_who_just_voted.name} a voté pour {self._human_vote_target.name}, mais il/elle est mort(e). Vote annulé.")
             else: print("ERREUR LOGIQUE: Acteur humain pour _human_vote_target non retrouvé.")
             # Nettoyer
             self._human_vote_target = None
             self._human_vote_target_actor_name = None
        # --- Fin traitement vote humain ---

        if not self.voters_to_process:
            # Tous les joueurs ont voté, résoudre
            print("DEBUG: Tous les votants traités. Résolution du vote...")
            self.master.after(500, self.resolve_vote_gui, self.current_votes)
            return

        voter = self.voters_to_process.pop(0)

        if not voter.is_alive:
            print(f"DEBUG: {voter.name} est mort avant de voter, passe.")
            self.master.after(50, self.process_next_voter)
            return

        if voter.is_human:
            # Humain doit voter
            self.current_human_actor = voter
            self.pending_action_type = "vote"
            self.possible_targets = [p for p in self.game.get_alive_players() if p != voter]
            self._human_vote_target_actor_name = voter.name

            self.action_prompt_label.config(text=f"Tour de Vote : {voter.name} ({voter.role.name})")
            self.log_message(f"\n{voter.name}, pour qui votez-vous ?")
            self.log_message("Sélectionnez un joueur et Confirmez.")

            self.players_listbox.config(selectmode=tk.SINGLE)
            self.players_listbox.selection_clear(0, tk.END)
            self._selected_target_for_human_action = None
            self.confirm_action_button.config(state=tk.DISABLED)
            self.pass_action_button.config(state=tk.DISABLED)

            return # STOP, attend input humain

        else: # IA vote
            if hasattr(voter, 'ai_logic') and voter.ai_logic:
                ia_target = voter.ai_logic.decide_vote()
                if ia_target and ia_target.is_alive:
                     self.current_votes[ia_target] = self.current_votes.get(ia_target, 0) + 1
                     print(f"DEBUG (Vote IA) : {voter.name} ({voter.role.name}) vote pour {ia_target.name}")
                else: print(f"DEBUG (Vote IA) : {voter.name} ({voter.role.name}) n'a pas voté ou cible invalide ({ia_target.name if ia_target else 'None'}).")
            else: print(f"ERREUR: IA {voter.name} n'a pas d'ai_logic pour voter.")

            # Passe au joueur suivant
            self.master.after(200, self.process_next_voter)


    def resolve_vote_gui(self, votes):
        """Résout le résultat du vote et applique le lynchage."""
        if not self.game or self.game.game_over: return
        self.action_prompt_label.config(text="Résolution du vote...")

        self.log_message("\n--- Résultat des votes ---")
        if not votes:
            self.log_message("Aucun vote enregistré. Personne n'est lynché.")
            lynched_player = None
        else:
            # Afficher décompte
            self.log_message("Décompte des votes :")
            sorted_players = sorted(self.game.players, key=lambda p: p.name)
            for player in sorted_players:
                if player.is_alive:
                    count = votes.get(player, 0)
                    self.log_message(f"- {player.name}: {count} voix")

            # Trouver max votes
            max_votes = 0
            for count in votes.values(): max_votes = max(max_votes, count)

            players_with_max_votes = [player for player, count in votes.items() if count == max_votes]

            if max_votes == 0:
                 self.log_message("Aucun vote contre un joueur. Personne n'est lynché.")
                 lynched_player = None
            elif len(players_with_max_votes) > 1:
                self.log_message(f"Égalité entre : {[p.name for p in players_with_max_votes]} ({max_votes} voix).")
                lynched_player = random.choice(players_with_max_votes)
                self.log_message(f"Après tirage au sort, {lynched_player.name} est lynché(e).")
            else:
                lynched_player = players_with_max_votes[0]
                self.log_message(f"{lynched_player.name} est lynché(e) avec {max_votes} vote(s).")

        # Appliquer lynchage
        if lynched_player and lynched_player.is_alive:
            self.game.lynched_this_day = lynched_player
            player_who_just_died = lynched_player # Store before die()
            player_who_just_died.die()
            self.update_player_list_display()
            self.log_message(f"Le rôle de {player_who_just_died.name} était {player_who_just_died.role.name}.")

            # Gérer Chasseur lynché
            if player_who_just_died.role.name == "Chasseur":
                 self.handle_hunter_sequence([player_who_just_died], self.check_victory_and_start_night_phase)
            else:
                 self.master.after(1000, self.check_victory_and_start_night_phase)
        else:
            self.log_message("Personne n'est éliminé aujourd'hui.")
            self.master.after(1000, self.check_victory_and_start_night_phase)


    def check_victory_and_start_night_phase(self):
        """Vérifie la victoire après le lynchage/chasseur et lance la nuit."""
        self.check_victory_and_proceed(self.start_night_phase)


    # ============================================
    # == GESTION DES ACTIONS UTILISATEUR (UI) ==
    # ============================================

    def confirm_human_action(self):
        """
        Gère le clic sur "Confirmer Action". Traite l'action humaine en attente.
        """
        target = self._selected_target_for_human_action

        if not target: messagebox.showwarning("Action Invalide", "Veuillez sélectionner un joueur cible."); return
        if target not in self.possible_targets:
            # Vérification spéciale pour la sorcière qui pourrait se sauver
            if not (self.pending_action_type == "Sorcière" and target == self.current_human_actor):
                 messagebox.showwarning("Action Invalide", "Cette cible n'est pas valide pour cette action."); return

        actor = self.current_human_actor
        action_type = self.pending_action_type # Sauvegarde avant clear

        # --- Désactiver UI ---
        self.players_listbox.config(selectmode=tk.DISABLED)
        self.players_listbox.selection_clear(0, tk.END)
        self.confirm_action_button.config(state=tk.DISABLED)
        self.pass_action_button.config(state=tk.DISABLED)
        self._selected_target_for_human_action = None
        current_actor_name = actor.name # Sauve le nom
        self.current_human_actor = None
        self.pending_action_type = None
        self.action_prompt_label.config(text="Action en cours...")
        # --- Fin désactivation ---

        print(f"DEBUG: Humain {current_actor_name} ({action_type}) confirme action sur {target.name}")

        # --- Appliquer l'action et continuer la séquence ---
        if action_type == "vote":
             self._human_vote_target = target
             self._human_vote_target_actor_name = current_actor_name
             # Log message will be handled by process_next_voter
             print(f"DEBUG: Vote humain de {current_actor_name} pour {target.name} prêt. Reprise séquence vote.")
             self.process_next_voter() # Reprend la séquence de vote

        elif action_type == "hunter_revenge":
            self.log_message(f"Le Chasseur {current_actor_name} élimine {target.name} en mourant.")
            target_was_already_dead = not target.is_alive
            target.die()
            if not target_was_already_dead and target.role.name == "Chasseur":
                 # Si le chasseur humain tue un autre chasseur, l'ajouter à la séquence suivante
                 print(f"DEBUG: Chasseur humain a tué un autre chasseur ({target.name}).")
                 # On doit trouver la liste des chasseurs restants et l'insérer. Géré par le callback.
                 # Le callback actuel est handle_hunter_sequence, il suffit de le rappeler.
                 pass # La séquence se poursuivra via le callback
            self.update_player_list_display()
            print("DEBUG: Action Chasseur vengeance humaine terminée. Appel callback.")
            if self._hunter_revenge_next_phase_callback:
                 callback = self._hunter_revenge_next_phase_callback
                 self._hunter_revenge_next_phase_callback = None
                 self.master.after(500, callback)

        elif action_type == "Loup-Garou":
             self.game.killed_this_night.append(target)
             self.log_message(f"{current_actor_name} (Loup) a choisi de dévorer {target.name}.")
             print("DEBUG: Action Loup-Garou humaine terminée. Reprise séquence nuit.")
             if hasattr(self, '_remaining_night_roles_after_human'):
                  remaining = self._remaining_night_roles_after_human
                  self._remaining_night_roles_after_human = []
                  self.master.after(100, self.execute_night_actions_sequence, remaining)
             else: print("ERREUR: _remaining_night_roles_after_human non trouvé."); self.master.after(500, self.resolve_night_gui)

        elif action_type == "Voyante":
             self.log_message(f"{current_actor_name} (Voyante) voit le rôle de {target.name} : {target.role.name}")
             print("DEBUG: Action Voyante humaine terminée. Reprise séquence nuit.")
             if hasattr(self, '_remaining_night_roles_after_human'):
                  remaining = self._remaining_night_roles_after_human
                  self._remaining_night_roles_after_human = []
                  self.master.after(100, self.execute_night_actions_sequence, remaining)
             else: print("ERREUR: _remaining_night_roles_after_human non trouvé."); self.master.after(500, self.resolve_night_gui)

    def pass_human_action(self):
        """Gère le clic sur "Passer l'action" (Voyante)."""
        actor = self.current_human_actor
        action_type = self.pending_action_type # Sauve avant clear

        if action_type == "Voyante":
            self.log_message(f"{actor.name} (Voyante) a décidé de ne pas espionner.")
            print(f"DEBUG: Humain {actor.name} ({action_type}) passe son tour.")

            # Désactiver UI
            self.players_listbox.config(selectmode=tk.DISABLED)
            self.players_listbox.selection_clear(0, tk.END)
            self.confirm_action_button.config(state=tk.DISABLED)
            self.pass_action_button.config(state=tk.DISABLED)
            self._selected_target_for_human_action = None
            self.current_human_actor = None
            self.pending_action_type = None
            self.action_prompt_label.config(text="Action en cours...")

            # Continuer séquence nuit
            if hasattr(self, '_remaining_night_roles_after_human'):
                 remaining = self._remaining_night_roles_after_human
                 self._remaining_night_roles_after_human = []
                 self.master.after(100, self.execute_night_actions_sequence, remaining)
            else: print("ERREUR: _remaining_night_roles_after_human non trouvé après PASS Voyante."); self.master.after(500, self.resolve_night_gui)
        else:
             messagebox.showwarning("Action Invalide", f"Le rôle {action_type} ne peut pas passer son tour.")


    # ============================================
    # == FIN DE PARTIE ET REINITIALISATION      ==
    # ============================================

    def end_game_gui(self):
        """Affiche le résultat final et propose de rejouer/quitter."""
        if not self.game: return

        self.log_message("\n--- PARTIE TERMINÉE ---")
        # Assurer que game_over est bien True
        self.game.game_over = True
        # Redéclenche la logique de victoire pour être sûr d'avoir le bon gagnant
        self.game.check_victory_condition()
        if self.game.winning_team:
            self.log_message(f"L'équipe gagnante est : {self.game.winning_team} !")
        else:
            self.log_message("La partie se termine sans vainqueur clair.")

        self.log_message("\nRévélation finale des rôles :")
        for player in self.game.players:
            status = "Vivant" if player.is_alive else "Mort"
            role_name = player.role.name if player.role else "Non défini"
            self.log_message(f"- {player.name} était {role_name} ({status})")

        self.update_player_list_display()

        # Désactiver interactions de jeu
        self.action_prompt_label.config(text="Partie terminée !")
        self.players_listbox.config(selectmode=tk.DISABLED)
        self.confirm_action_button.config(state=tk.DISABLED)
        self.pass_action_button.config(state=tk.DISABLED)
        self.current_human_actor = None
        self.pending_action_type = None

        # Supprimer bouton débat
        if hasattr(self, '_pass_vote_button') and self._pass_vote_button.winfo_exists(): self._pass_vote_button.destroy()

        # Ajouter boutons fin de partie s'ils n'existent pas déjà
        if not hasattr(self, '_end_game_buttons_frame') or not self._end_game_buttons_frame.winfo_exists():
            self._end_game_buttons_frame = tk.Frame(self.action_info_frame)
            self._end_game_buttons_frame.pack(pady=20)
            tk.Button(self._end_game_buttons_frame, text="Nouvelle Partie", command=self.reset_game).pack(side=tk.LEFT, padx=5)
            tk.Button(self._end_game_buttons_frame, text="Quitter", command=self.master.quit).pack(side=tk.LEFT, padx=5)


    def reset_game(self):
        """Réinitialise l'interface et les données pour une nouvelle partie."""
        # Détruire les boutons spécifiques
        if hasattr(self, '_end_game_buttons_frame') and self._end_game_buttons_frame.winfo_exists(): self._end_game_buttons_frame.destroy()
        if hasattr(self, '_pass_vote_button') and self._pass_vote_button.winfo_exists(): self._pass_vote_button.destroy()

        # Réinitialiser les variables d'état
        self.game = None
        self.current_human_actor = None
        self.pending_action_type = None
        self.possible_targets = []
        self._selected_target_for_human_action = None
        self._human_vote_target = None
        self._human_vote_target_actor_name = None
        self.voters_to_process = []
        self.current_votes = {}
        self._remaining_night_roles_after_human = []
        self._hunter_revenge_next_phase_callback = None

        # Nettoyer les widgets du jeu
        self.message_area.config(state=tk.NORMAL)
        self.message_area.delete(1.0, tk.END)
        self.message_area.config(state=tk.DISABLED)
        self.players_listbox.delete(0, tk.END)
        self.human_role_label.config(text="")
        self.action_prompt_label.config(text="")

        # Revenir à la frame de configuration
        self.show_frame(self.config_frame)
        self.log_message("\n--- Nouvelle Partie ---")
        self.log_message("Configurez les paramètres et démarrez.")

# --- Point d'entrée (dans main.py) ---
# import tkinter as tk
# from gui import GameGUI
# if __name__ == "__main__":
#     root = tk.Tk()
#     app = GameGUI(root)
#     root.mainloop()