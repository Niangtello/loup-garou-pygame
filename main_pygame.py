# main_pygame.py
import pygame
import sys
import os # Pour joindre les chemins d'accès aux fichiers
import random
import time # Pour les délais non bloquants

# Importer la logique du jeu depuis les autres fichiers
from game import Game
from player import Player
from roles import get_available_roles
from ai import create_ai_logic # Assurez-vous que cette fonction existe dans ai.py

# --- Constantes ---
LARGEUR_ECRAN, HAUTEUR_ECRAN = 1000, 750
FPS = 60

# Couleurs (RVB)
BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
ROUGE = (180, 0, 0)
GRIS_FONCE = (40, 40, 40)
GRIS_CLAIR = (100, 100, 100)
JAUNE_LUNE = (240, 230, 140)
BLEU_NUIT = (25, 25, 112)
VERT_POTION = (0, 100, 0)
ORANGE_INFO = (255, 165, 0)

# États du jeu (pour gérer le flux)
ETAT_CONFIG = "CONFIGURATION"
ETAT_NUIT_SEQUENCE = "NUIT_SEQUENCE"
ETAT_NUIT_ATTENTE_HUMAIN = "NUIT_ATTENTE_HUMAIN"
ETAT_NUIT_RESOLUTION = "NUIT_RESOLUTION"
ETAT_CHASSEUR_SEQUENCE = "CHASSEUR_SEQUENCE"
ETAT_CHASSEUR_ATTENTE_HUMAIN = "CHASSEUR_ATTENTE_HUMAIN"
ETAT_JOUR_DEBAT = "JOUR_DEBAT"
ETAT_JOUR_VOTE_SEQUENCE = "JOUR_VOTE_SEQUENCE"
ETAT_JOUR_VOTE_ATTENTE_HUMAIN = "JOUR_VOTE_ATTENTE_HUMAIN"
ETAT_JOUR_VOTE_RESOLUTION = "JOUR_VOTE_RESOLUTION"
ETAT_FIN_PARTIE = "FIN_PARTIE"


# --- Fonctions Utilitaires ---

def charger_image(nom_fichier, utiliser_alpha=False):
    """Charge une image depuis le dossier 'images'."""
    chemin_complet = os.path.join("images", nom_fichier)
    try:
        image = pygame.image.load(chemin_complet)
        if utiliser_alpha:
            image = image.convert_alpha() # Pour la transparence
        else:
            image = image.convert()
        return image
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'image '{chemin_complet}': {e}")
        # Retourner une surface vide ou placeholder si l'image manque
        surface_vide = pygame.Surface((50, 50), pygame.SRCALPHA) # SRCALPHA pour transparence placeholder
        pygame.draw.rect(surface_vide, ROUGE, surface_vide.get_rect(), 2) # Dessine un carré rouge
        # Utiliser une police par défaut chargée après l'init de pygame.font
        if pygame.font.get_init():
            police_erreur = pygame.font.Font(None, 30)
            dessiner_texte(surface_vide, "?", police_erreur, ROUGE, surface_vide.get_rect())
        return surface_vide

def charger_police(nom_fichier, taille):
    """Charge une police depuis le dossier 'fonts' ou une police système."""
    if nom_fichier:
        chemin_complet = os.path.join("fonts", nom_fichier)
        try:
            return pygame.font.Font(chemin_complet, taille)
        except pygame.error as e:
            print(f"Erreur lors du chargement de la police '{chemin_complet}', utilisation de la police par défaut: {e}")
    # Si fichier non spécifié ou erreur, utiliser police par défaut
    # S'assurer que pygame.font est initialisé avant d'appeler Font(None,...)
    if not pygame.font.get_init():
        pygame.font.init() # Initialiser si ce n'est pas déjà fait
    return pygame.font.Font(None, taille) # Police système par défaut

def dessiner_texte(surface, texte, police, couleur, rect_ou_pos, alignement="center", anti_alias=True, couleur_fond=None):
    """Dessine du texte sur une surface à une position donnée ou dans un rect."""
    try:
        texte_surface = police.render(texte, anti_alias, couleur, couleur_fond)
        texte_rect = texte_surface.get_rect()
        if isinstance(rect_ou_pos, pygame.Rect):
            # Alignement dans un Rect
            if alignement == "center": texte_rect.center = rect_ou_pos.center
            elif alignement == "topleft": texte_rect.topleft = rect_ou_pos.topleft
            elif alignement == "midtop": texte_rect.midtop = rect_ou_pos.midtop
            elif alignement == "midleft": texte_rect.midleft = rect_ou_pos.midleft
            elif alignement == "midright": texte_rect.midright = rect_ou_pos.midright
            elif alignement == "midbottom": texte_rect.midbottom = rect_ou_pos.midbottom
            elif alignement == "bottomleft": texte_rect.bottomleft = rect_ou_pos.bottomleft
            elif alignement == "bottomright": texte_rect.bottomright = rect_ou_pos.bottomright
            else: texte_rect.center = rect_ou_pos.center # Par défaut center
        else: # Position absolue (tuple/list)
             if alignement == "center": texte_rect.center = rect_ou_pos
             elif alignement == "topleft": texte_rect.topleft = rect_ou_pos
             elif alignement == "midtop": texte_rect.midtop = rect_ou_pos
             # Ajouter d'autres si besoin
             else: texte_rect.center = rect_ou_pos

        surface.blit(texte_surface, texte_rect)
        return texte_rect
    except Exception as e:
        print(f"Erreur lors du dessin du texte '{texte}': {e}")
        return pygame.Rect(0,0,0,0)

# --- Classes UI ---

class Bouton:
    """Classe simple pour créer des boutons cliquables."""
    def __init__(self, x, y, largeur, hauteur, texte='', couleur_fond=GRIS_CLAIR, couleur_survol=GRIS_CLAIR, couleur_desactive=GRIS_FONCE, couleur_texte=BLANC, police=None, image=None, image_survol=None, image_desactive=None, callback=None):
        self.rect = pygame.Rect(x, y, largeur, hauteur)
        self.texte = texte
        self.couleur_fond = couleur_fond
        self.couleur_survol = couleur_survol
        self.couleur_desactive = couleur_desactive
        self.couleur_texte = couleur_texte
        self.police = police if police else charger_police(None, 20)
        self.image = image
        self.image_survol = image_survol if image_survol else image
        self.image_desactive = image_desactive if image_desactive else image
        self.callback = callback
        self.survol = False
        self.actif = True

    def dessiner(self, surface):
        image_a_afficher = self.image
        couleur_fond_actuelle = self.couleur_fond

        if not self.actif: image_a_afficher = self.image_desactive if self.image_desactive else self.image; couleur_fond_actuelle = self.couleur_desactive
        elif self.survol: image_a_afficher = self.image_survol if self.image_survol else self.image; couleur_fond_actuelle = self.couleur_survol
        else: image_a_afficher = self.image; couleur_fond_actuelle = self.couleur_fond

        if image_a_afficher:
            try: image_resized = pygame.transform.scale(image_a_afficher, (self.rect.width, self.rect.height)); surface.blit(image_resized, self.rect.topleft)
            except Exception as e: print(f"Erreur dessin image bouton '{self.texte}': {e}"); pygame.draw.rect(surface, couleur_fond_actuelle, self.rect, border_radius=5) # Fallback
        else: pygame.draw.rect(surface, couleur_fond_actuelle, self.rect, border_radius=5)

        if self.texte:
            couleur_txt = self.couleur_texte if self.actif else tuple(c // 2 for c in self.couleur_texte)
            dessiner_texte(surface, self.texte, self.police, couleur_txt, self.rect)

    def gerer_evenement(self, event):
        retour_action = None
        pos_souris = pygame.mouse.get_pos(); self.survol = self.rect.collidepoint(pos_souris)
        if self.actif and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.survol:
            print(f"DEBUG: Bouton '{self.texte}' cliqué.")
            if self.callback: retour_action = self.callback()
        return retour_action

class CarteJoueur:
    """Représente visuellement une carte de joueur."""
    TAILLE_CARTE = (100, 140); ESPACEMENT = 15

    def __init__(self, joueur, x, y, police_nom, police_statut, image_carte=None, icones_roles=None, icone_mort=None):
        self.joueur = joueur; self.rect = pygame.Rect(x, y, self.TAILLE_CARTE[0], self.TAILLE_CARTE[1])
        self.police_nom = police_nom; self.police_statut = police_statut
        self.image_carte_base = image_carte # N'est plus utilisé dans dessiner() V2
        self.icones_roles = icones_roles if icones_roles else {}; self.icone_mort = icone_mort
        self.survol = False; self.selectionne = False; self.peut_etre_cible = False; self.afficher_role = False

    def dessiner(self, surface):
        # --- VERSION MODIFIÉE : Ignore carte_dos.jpg et dessine un fond ---
        couleur_fond = GRIS_FONCE
        if not self.joueur.is_alive: couleur_fond = tuple(c // 2 for c in GRIS_FONCE)
        elif self.selectionne: couleur_fond = JAUNE_LUNE
        elif self.survol and self.peut_etre_cible: couleur_fond = GRIS_CLAIR
        elif self.survol: couleur_fond = tuple(min(255, c + 20) for c in GRIS_FONCE)

        pygame.draw.rect(surface, couleur_fond, self.rect, border_radius=8)

        overlay = pygame.Surface(self.TAILLE_CARTE, pygame.SRCALPHA)
        if self.selectionne: overlay.fill((*BLANC, 50))
        elif self.survol and self.peut_etre_cible: overlay.fill((*BLANC, 30))
        surface.blit(overlay, self.rect.topleft)

        if self.peut_etre_cible: pygame.draw.rect(surface, ORANGE_INFO, self.rect, width=3, border_radius=8)
        elif self.selectionne: pygame.draw.rect(surface, BLANC, self.rect, width=3, border_radius=8)

        nom_rect = self.rect.inflate(-10, -10)
        dessiner_texte(surface, self.joueur.name, self.police_nom, BLANC, nom_rect, alignement="midtop")

        role_a_afficher = self.joueur.role.name if self.joueur.role else None
        if role_a_afficher and (self.afficher_role):
             icone = self.icones_roles.get(role_a_afficher)
             if icone:
                 try:
                    icone_scaled = pygame.transform.smoothscale(icone, (40, 40)); icone_rect = icone_scaled.get_rect(centerx=self.rect.centerx, centery=self.rect.centery + 10)
                    surface.blit(icone_scaled, icone_rect)
                 except Exception as e: print(f"Erreur affichage icone role {role_a_afficher}: {e}")

        if not self.joueur.is_alive:
            if self.icone_mort:
                try:
                    icone_mort_scaled = pygame.transform.smoothscale(self.icone_mort, (50, 50)); mort_rect = icone_mort_scaled.get_rect(center=self.rect.center)
                    surface.blit(icone_mort_scaled, mort_rect)
                except Exception as e: print(f"Erreur affichage icone mort: {e}")
            else: # Fallback texte
                statut_rect = pygame.Rect(self.rect.left + 5, self.rect.centery - 10, self.rect.width - 10, 20)
                dessiner_texte(surface, "Mort", self.police_statut, ROUGE, statut_rect, alignement="center")

    def gerer_evenement(self, event):
        pos_souris = pygame.mouse.get_pos(); self.survol = self.rect.collidepoint(pos_souris)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.survol: return self.joueur
        return None

# --- Classe Principale de l'Application Pygame ---

class GameApp:
    def __init__(self):
        try:
            pygame.init(); pygame.mixer.init()
            self.ecran = pygame.display.set_mode((LARGEUR_ECRAN, HAUTEUR_ECRAN))
            pygame.display.set_caption("Loup Garou de Thiercelieux - Édition Pygame")
            self.horloge = pygame.time.Clock()
            self.jeu = None; self.etat_jeu = ETAT_CONFIG; self.en_cours = True
            self.charger_assets()
            self.widgets_config = self.creer_widgets_config(); self.cartes_joueurs_visuels = []; self.boutons_jeu = {}; self.log_messages_jeu = []
            self.creer_widgets_jeu()
            self.acteur_humain_actuel = None; self.action_humaine_attendue = None; self.cibles_possibles_action = []; self.cible_humaine_selectionnee = None
            self.delai_prochaine_action = 0; self.sequence_nuit_restante = []; self.votants_restants = []; self.votes_en_cours = {}
            self.chasseurs_morts_sequence = []; self.callback_apres_chasseur = None
        except Exception as e:
             print("\n*** ERREUR INIT ***"); print(f"Erreur: {e}"); print("Vérifiez Pygame, dossiers 'images', 'fonts'."); print("******************\n")
             self.en_cours = False
             try: # Message erreur graphique
                 pygame.font.init(); police_erreur = pygame.font.Font(None, 30); msg1 = police_erreur.render("Erreur fatale initialisation.", True, ROUGE, NOIR); msg2 = police_erreur.render("Verifier console.", True, ROUGE, NOIR)
                 screen_error = pygame.display.set_mode((600, 100)); screen_error.blit(msg1, (10, 10)); screen_error.blit(msg2, (10, 50)); pygame.display.flip()
                 while True:
                      for event in pygame.event.get():
                          if event.type == pygame.QUIT or event.type == pygame.KEYDOWN: pygame.quit(); sys.exit()
             except: pygame.quit(); sys.exit()

    def charger_assets(self):
        """Charge toutes les images et polices nécessaires."""
        print("Chargement des assets...")
        # --- Polices ---
        self.polices = {
            "titre": charger_police("Cinzel-Regular.ttf", 48),      # Police Titre
            "normal": charger_police("EBGaramond-Regular.ttf", 18), # Police Principale
            "bouton": charger_police("EBGaramond-Bold.ttf", 20),    # Police Boutons
            "carte_nom": charger_police("EBGaramond-Regular.ttf", 16), # Police Nom Carte
            "carte_statut": charger_police("EBGaramond-Regular.ttf", 14), # Police Statut Carte
        }
        # --- Images ---
        self.images = {
            "fond_config": charger_image("fond_village.jpg"), "fond_nuit": charger_image("fond_foret_nuit.jpg"), "fond_jour": charger_image("fond_village_jour.jpg"),
            "carte_base": charger_image("carte_dos.jpg", utiliser_alpha=False), # Utilise .jpg
            "icone_loup": charger_image("icone_loup.png", utiliser_alpha=True), "icone_villageois": charger_image("icone_villageois.png", utiliser_alpha=True),
            "icone_voyante": charger_image("icone_voyante.png", utiliser_alpha=True), "icone_sorciere": charger_image("icone_sorciere.png", utiliser_alpha=True),
            "icone_chasseur": charger_image("icone_chasseur.png", utiliser_alpha=True), "icone_mort": charger_image("icone_crane.png", utiliser_alpha=True),
            "soleil": charger_image("icone_soleil.png", utiliser_alpha=True), "lune": charger_image("icone_lune.png", utiliser_alpha=True),
        }
        self.icones_roles_map = {
            "Loup-Garou": self.images.get("icone_loup"), "Villageois": self.images.get("icone_villageois"), "Voyante": self.images.get("icone_voyante"),
            "Sorcière": self.images.get("icone_sorciere"), "Chasseur": self.images.get("icone_chasseur"),
        }
        try: # Redimensionner fonds
            self.images["fond_config"] = pygame.transform.scale(self.images["fond_config"], (LARGEUR_ECRAN, HAUTEUR_ECRAN))
            self.images["fond_nuit"] = pygame.transform.scale(self.images["fond_nuit"], (LARGEUR_ECRAN, HAUTEUR_ECRAN))
            self.images["fond_jour"] = pygame.transform.scale(self.images["fond_jour"], (LARGEUR_ECRAN, HAUTEUR_ECRAN))
        except Exception as e: print(f"Erreur redimensionnement fonds: {e}")
        print("Assets chargés.")

    def creer_widgets_config(self):
        widgets = {}; widgets["bouton_demarrer"] = Bouton(LARGEUR_ECRAN // 2 - 150, HAUTEUR_ECRAN - 100, 300, 50, texte="Démarrer Partie (Config Auto 5 Joueurs)", couleur_fond=(50, 100, 50), couleur_survol=(70, 140, 70), police=self.polices["bouton"], callback=self.demarrer_partie_config_auto); return widgets

    def creer_widgets_jeu(self):
        self.rect_zone_messages = pygame.Rect(50, HAUTEUR_ECRAN - 170, LARGEUR_ECRAN - 100, 150)
        btn_w, btn_h = 180, 40; btn_x = LARGEUR_ECRAN - btn_w - 20 # Position X commune
        self.boutons_jeu["confirmer"] = Bouton(btn_x, HAUTEUR_ECRAN - btn_h*3 - 40, btn_w, btn_h, texte="Confirmer Action", police=self.polices["bouton"], callback=self.confirmer_action_humaine, couleur_fond=(0,100,0), couleur_survol=(0,150,0))
        self.boutons_jeu["passer"] = Bouton(btn_x, HAUTEUR_ECRAN - btn_h*2 - 30, btn_w, btn_h, texte="Passer l'Action", police=self.polices["bouton"], callback=self.passer_action_humaine, couleur_fond=(100,100,0), couleur_survol=(150,150,0))
        self.boutons_jeu["passer_au_vote"] = Bouton(LARGEUR_ECRAN // 2 - 100, 20, 200, 40, texte="Passer au Vote", police=self.polices["bouton"], callback=self.lancer_phase_vote, couleur_fond=(0,0,100), couleur_survol=(0,0,150))
        self.boutons_jeu["nouvelle_partie"] = Bouton(LARGEUR_ECRAN // 2 - 210, HAUTEUR_ECRAN - 70, 200, 50, texte="Nouvelle Partie", police=self.polices["bouton"], callback=self.reinitialiser_jeu, couleur_fond=(50,50,100), couleur_survol=(70,70,140))
        self.boutons_jeu["quitter"] = Bouton(LARGEUR_ECRAN // 2 + 10, HAUTEUR_ECRAN - 70, 200, 50, texte="Quitter", police=self.polices["bouton"], callback=self.quitter_jeu, couleur_fond=(100,50,50), couleur_survol=(140,70,70))
        for btn in self.boutons_jeu.values(): btn.actif = False

    def demarrer_partie_config_auto(self):
        try:
            total_joueurs = 5; num_humains = 1; roles_config = {'Loup-Garou': 1, 'Voyante': 1, 'Sorcière': 1, 'Villageois': 2}
            self.log_message_jeu(f"Démarrage config auto: {total_joueurs}J ({num_humains}H), Rôles: {roles_config}"); print(f"DEBUG: Config: {roles_config}")
            self.jeu = Game(); human_names = []
            for i in range(num_humains): name = f"Joueur {i+1}"; human_names.append(name); self.jeu.add_player(Player(name, is_human=True))
            num_ia = total_joueurs - num_humains; ia_index = 1; num_ia_added = 0
            for _ in range(num_ia):
                player_added = False; loop_guard = 0
                while not player_added:
                    name = f"IA_{ia_index}";
                    if not self.jeu.get_player_by_name(name): self.jeu.add_player(Player(name, is_human=False)); player_added = True; num_ia_added += 1
                    ia_index += 1;
                    if loop_guard > total_joueurs * 3: raise Exception("Boucle infinie nom IA");
                    loop_guard+=1
            print(f"DEBUG: Ajouté {num_ia_added} IA.")
            if len(self.jeu.players) != total_joueurs: raise Exception(f"Incohérence joueurs créés {len(self.jeu.players)} != total {total_joueurs}")
            if self.jeu.assign_roles(roles_config):
                for player in self.jeu.players:
                    if not player.is_human: player.ai_logic = create_ai_logic(player, self.jeu)
                self.log_message_jeu("Partie commence !"); self.log_message_jeu(f"Humains: {', '.join(human_names)}"); self.log_message_jeu("Distribution rôles...")
                for player in self.jeu.players:
                     if player.is_human: self.log_message_jeu(f"IMPORTANT: {player.name}, rôle : {player.role.name}")
                self.organiser_cartes_joueurs(); self.etat_jeu = ETAT_NUIT_SEQUENCE; self.lancer_phase_nuit()
            else: self.log_message_jeu("Erreur assignation rôles."); self.etat_jeu = ETAT_CONFIG
        except Exception as e: self.log_message_jeu(f"Erreur démarrage: {e}"); print(f"ERREUR démarrage: {e}"); self.etat_jeu = ETAT_CONFIG

    def organiser_cartes_joueurs(self):
        self.cartes_joueurs_visuels = [];
        if not self.jeu: return; nb_joueurs = len(self.jeu.players); max_par_ligne = 5;
        largeur_totale_ligne_max = min(nb_joueurs, max_par_ligne) * (CarteJoueur.TAILLE_CARTE[0] + CarteJoueur.ESPACEMENT) - CarteJoueur.ESPACEMENT
        start_y = 50
        for i, joueur in enumerate(self.jeu.players):
            ligne = i // max_par_ligne; colonne = i % max_par_ligne
            joueurs_cette_ligne = min(max_par_ligne, nb_joueurs - ligne * max_par_ligne); largeur_cette_ligne = joueurs_cette_ligne * (CarteJoueur.TAILLE_CARTE[0] + CarteJoueur.ESPACEMENT) - CarteJoueur.ESPACEMENT
            start_x = (LARGEUR_ECRAN - largeur_cette_ligne) // 2
            x = start_x + colonne * (CarteJoueur.TAILLE_CARTE[0] + CarteJoueur.ESPACEMENT); y = start_y + ligne * (CarteJoueur.TAILLE_CARTE[1] + CarteJoueur.ESPACEMENT)
            carte = CarteJoueur(joueur, x, y, self.polices["carte_nom"], self.polices["carte_statut"], self.images.get("carte_base"), self.icones_roles_map, self.images.get("icone_mort")); self.cartes_joueurs_visuels.append(carte)

    def log_message_jeu(self, message):
        print(f"LOG: {message}"); self.log_messages_jeu.append(message)
        max_log_lines = 7;
        if len(self.log_messages_jeu) > max_log_lines: self.log_messages_jeu = self.log_messages_jeu[-max_log_lines:]

    def quitter_jeu(self): self.en_cours = False

    def run(self):
        while self.en_cours:
            temps_actuel = pygame.time.get_ticks()
            self.gerer_evenements()
            if self.jeu: self.mettre_a_jour_logique(temps_actuel)
            self.dessiner_ecran()
            self.horloge.tick(FPS)
        print("Arrêt Pygame."); pygame.quit(); sys.exit()

    def gerer_evenements(self):
        self.cible_humaine_selectionnee = None
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT: self.en_cours = False

            boutons_actifs = [];
            if self.etat_jeu == ETAT_CONFIG: boutons_actifs = [self.widgets_config["bouton_demarrer"]]
            elif self.etat_jeu == ETAT_FIN_PARTIE: boutons_actifs = [self.boutons_jeu["nouvelle_partie"], self.boutons_jeu["quitter"]]
            else: boutons_actifs = [btn for btn in self.boutons_jeu.values() if btn.actif]
            for btn in boutons_actifs: btn.gerer_evenement(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                 if self.etat_jeu in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN] and not any(btn.survol for btn in boutons_actifs):
                    for carte in self.cartes_joueurs_visuels:
                        joueur_clique = carte.gerer_evenement(event)
                        if joueur_clique:
                            if joueur_clique in self.cibles_possibles_action:
                                self.cible_humaine_selectionnee = joueur_clique; self.boutons_jeu["confirmer"].actif = True; print(f"DEBUG: Cible {joueur_clique.name} sélectionnée.")
                            else: print(f"DEBUG: Clic sur {joueur_clique.name} non ciblable."); self.cible_humaine_selectionnee = None; self.boutons_jeu["confirmer"].actif = False # Désélectionne si clic hors cible
                            for c in self.cartes_joueurs_visuels: c.selectionne = (c.joueur == self.cible_humaine_selectionnee) # Met à jour sélection visuelle
                            break

    def mettre_a_jour_logique(self, temps_actuel):
        if not self.jeu or self.etat_jeu == ETAT_FIN_PARTIE: return
        if self.jeu.game_over and self.etat_jeu != ETAT_FIN_PARTIE: self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie(); return
        if temps_actuel < self.delai_prochaine_action: return

        if self.etat_jeu == ETAT_NUIT_SEQUENCE: self.executer_action_nuit_suivante()
        elif self.etat_jeu == ETAT_NUIT_RESOLUTION: self.resoudre_nuit()
        elif self.etat_jeu == ETAT_CHASSEUR_SEQUENCE: self.executer_action_chasseur_suivante()
        elif self.etat_jeu == ETAT_JOUR_VOTE_SEQUENCE: self.traiter_votant_suivant()
        elif self.etat_jeu == ETAT_JOUR_VOTE_RESOLUTION: self.resoudre_vote()

    def dessiner_ecran(self):
        if self.etat_jeu == ETAT_CONFIG: self.dessiner_ecran_config()
        elif self.etat_jeu != ETAT_CONFIG: self.dessiner_ecran_jeu()
        pygame.display.flip()

    def dessiner_ecran_config(self):
        self.ecran.blit(self.images["fond_config"], (0, 0)); dessiner_texte(self.ecran, "Loup Garou", self.polices["titre"], JAUNE_LUNE, (LARGEUR_ECRAN // 2, 80))
        self.widgets_config["bouton_demarrer"].dessiner(self.ecran); y_log = 150
        for message in self.log_messages_jeu: dessiner_texte(self.ecran, message, self.polices["normal"], BLANC, (LARGEUR_ECRAN // 2, y_log), alignement="center"); y_log += self.polices["normal"].get_height() + 2

    def dessiner_ecran_jeu(self):
        fond = self.images["fond_jour"] if self.jeu and self.jeu.is_day else self.images["fond_nuit"]
        self.ecran.blit(fond, (0,0))
        pos_souris = pygame.mouse.get_pos()
        for carte in self.cartes_joueurs_visuels:
            carte.survol = carte.rect.collidepoint(pos_souris)
            carte.peut_etre_cible = (self.etat_jeu in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN]) and carte.joueur in self.cibles_possibles_action
            carte.selectionne = (self.cible_humaine_selectionnee == carte.joueur)
            carte.afficher_role = (self.etat_jeu == ETAT_FIN_PARTIE)
            carte.dessiner(self.ecran)

        fond_log = (*GRIS_FONCE, 200); log_surface = pygame.Surface((self.rect_zone_messages.width, self.rect_zone_messages.height), pygame.SRCALPHA); log_surface.fill(fond_log)
        y_log = log_surface.get_height() - self.polices["normal"].get_height() - 5
        for message in reversed(self.log_messages_jeu): dessiner_texte(log_surface, message, self.polices["normal"], BLANC, (10, y_log), alignement="bottomleft"); y_log -= self.polices["normal"].get_height() + 2;
        if y_log < 0: break
        self.ecran.blit(log_surface, self.rect_zone_messages.topleft)

        icone_phase = self.images.get("soleil") if self.jeu and self.jeu.is_day else self.images.get("lune")
        if icone_phase:
            try: icone_phase_scaled = pygame.transform.smoothscale(icone_phase, (60, 60)); rect_phase = icone_phase_scaled.get_rect(topright=(LARGEUR_ECRAN - 20, 20)); self.ecran.blit(icone_phase_scaled, rect_phase)
            except Exception as e: print(f"Erreur dessin icone phase: {e}")

        for nom, btn in self.boutons_jeu.items():
            afficher = False;
            if self.etat_jeu == ETAT_FIN_PARTIE and nom in ["nouvelle_partie", "quitter"]: afficher = True
            elif self.etat_jeu == ETAT_JOUR_DEBAT and nom == "passer_au_vote": afficher = True
            elif self.etat_jeu in [ETAT_NUIT_ATTENTE_HUMAIN, ETAT_JOUR_VOTE_ATTENTE_HUMAIN, ETAT_CHASSEUR_ATTENTE_HUMAIN] and nom in ["confirmer", "passer"]:
                 if self.acteur_humain_actuel: afficher = True

            if afficher: # Dessiner seulement si affichable ET logiquement actif/inactif
                 # Le bouton gère son apparence actif/inactif dans son propre draw
                 btn.dessiner(self.ecran)


    def executer_action_nuit_suivante(self):
        if not self.jeu or self.jeu.game_over: self.verifier_victoire_et_lancer_jour(); return # Sécurité
        if not self.sequence_nuit_restante: self.etat_jeu = ETAT_NUIT_RESOLUTION; self.delai_prochaine_action = pygame.time.get_ticks() + 500; return

        role_actuel = self.sequence_nuit_restante.pop(0); joueurs_actifs = [p for p in self.jeu.get_alive_players() if p.role.name == role_actuel]
        if not joueurs_actifs: print(f"DEBUG: Nuit - Pas de joueur {role_actuel}"); self.delai_prochaine_action = pygame.time.get_ticks() + 50; self.etat_jeu = ETAT_NUIT_SEQUENCE; return

        acteur_humain = next((p for p in joueurs_actifs if p.is_human), None)
        if acteur_humain:
            if role_actuel == "Sorcière" and not (acteur_humain.has_saved_potion or acteur_humain.has_kill_potion): self.log_message_jeu(f"{acteur_humain.name} (Sorcière) sans potions."); self.delai_prochaine_action = pygame.time.get_ticks() + 500; self.etat_jeu = ETAT_NUIT_SEQUENCE
            elif role_actuel == "Chasseur": self.delai_prochaine_action = pygame.time.get_ticks() + 50; self.etat_jeu = ETAT_NUIT_SEQUENCE
            else:
                 if role_actuel == "Sorcière": att = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None; self.sorciere_action_popup(acteur_humain, att, self.sequence_nuit_restante[:]) # Passer copie
                 else: self.preparer_action_humaine(acteur_humain, role_actuel)
                 self.etat_jeu = ETAT_NUIT_ATTENTE_HUMAIN; return # STOP
        else: # IA
            print(f"DEBUG: Nuit - IA {role_actuel}...");
            if role_actuel == "Loup-Garou":
                ia = joueurs_actifs[0];
                if hasattr(ia, 'ai_logic') and ia.ai_logic: c = ia.ai_logic.decide_night_action();
                if c and c.is_alive: self.jeu.killed_this_night.append(c); print(f"DEBUG: Loup IA -> {c.name}")
            elif role_actuel == "Voyante":
                for ia in joueurs_actifs:
                     if hasattr(ia, 'ai_logic') and ia.ai_logic: ia.ai_logic.decide_night_action()
            elif role_actuel == "Sorcière":
                 actives = [p for p in joueurs_actifs if (p.has_saved_potion or p.has_kill_potion)]
                 for ia in actives:
                      if hasattr(ia, 'ai_logic') and ia.ai_logic:
                           att = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None
                           if att: att.is_attacked_this_night = True
                           else: for p in self.jeu.players: p.is_attacked_this_night = False
                           act = ia.ai_logic.decide_night_action()
                           if act["save"] and ia.has_saved_potion and act["save"].is_alive: self.jeu.saved_this_night = act["save"]; ia.has_saved_potion = False; print(f"DEBUG: Sorc IA save {act['save'].name}")
                           if act["kill"] and ia.has_kill_potion and self.jeu.saved_this_night is None and act["kill"].is_alive: self.jeu.potioned_to_death_this_night = act["kill"]; ia.has_kill_potion = False; print(f"DEBUG: Sorc IA kill {act['kill'].name}")
            self.delai_prochaine_action = pygame.time.get_ticks() + 750; self.etat_jeu = ETAT_NUIT_SEQUENCE

    def preparer_action_humaine(self, acteur, type_action):
        self.acteur_humain_actuel = acteur; self.action_humaine_attendue = type_action; self.cible_humaine_selectionnee = None; self.boutons_jeu["confirmer"].actif = False; self.boutons_jeu["passer"].actif = False; peut_passer = False; cibles = []; prompt = ""; log_prefix = f"\n{acteur.name} ({acteur.role.name}), à vous."
        if type_action == "Loup-Garou": prompt = "Qui dévorer ?"; cibles = [p for p in self.jeu.get_alive_players() if p.role and not p.role.is_wolf] # Vérifier p.role existe
        elif type_action == "Voyante": prompt = "Qui espionner ?"; cibles = [p for p in self.jeu.get_alive_players() if p != acteur]; peut_passer = True
        elif type_action == "Vote": prompt = "Pour qui voter ?"; cibles = [p for p in self.jeu.get_alive_players() if p != acteur]
        elif type_action == "Chasseur": prompt = "Qui éliminer ?"; cibles = self.jeu.get_alive_players()
        self.cibles_possibles_action = cibles; self.log_message_jeu(log_prefix); self.log_message_jeu(prompt); self.log_message_jeu("Sélectionnez une carte et confirmez."); self.boutons_jeu["passer"].actif = peut_passer
        for carte in self.cartes_joueurs_visuels: carte.selectionne = False

    def confirmer_action_humaine(self):
        if not self.acteur_humain_actuel or not self.action_humaine_attendue or not self.cible_humaine_selectionnee: return
        acteur = self.acteur_humain_actuel; action = self.action_humaine_attendue; cible = self.cible_humaine_selectionnee; current_actor_name = acteur.name
        print(f"DEBUG: Humain {current_actor_name} ({action}) confirme sur {cible.name}")
        self.players_listbox.config(selectmode=tk.DISABLED); self.players_listbox.selection_clear(0, tk.END); self.confirm_action_button.config(state=tk.DISABLED); self.pass_action_button.config(state=tk.DISABLED); self._selected_target_for_human_action = None; self.current_human_actor = None; self.pending_action_type = None; self.action_prompt_label.config(text="Action en cours...") # Tkinter code restant ? A supprimer

        # --- Désactivation UI Pygame ---
        self.boutons_jeu["confirmer"].actif = False; self.boutons_jeu["passer"].actif = False
        self.cible_humaine_selectionnee = None; self.acteur_humain_actuel = None; self.action_humaine_attendue = None
        for carte in self.cartes_joueurs_visuels: carte.selectionne = False
        # --- Fin Désactivation ---


        if action == "Loup-Garou": self.jeu.killed_this_night.append(cible); self.log_message_jeu(f"Vous dévorez {cible.name}."); self.etat_jeu = ETAT_NUIT_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 200
        elif action == "Voyante": self.log_message_jeu(f"Rôle de {cible.name} : {cible.role.name}"); self.etat_jeu = ETAT_NUIT_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 200
        elif action == "Vote": self._human_vote_target = cible; self._human_vote_target_actor_name = current_actor_name; print(f"DEBUG: Vote Humain {current_actor_name} -> {cible.name} prêt."); self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE; self.traiter_votant_suivant() # Traiter immédiatement après confirmation
        elif action == "Chasseur":
             self.log_message_jeu(f"Chasseur {current_actor_name} élimine {cible.name} !"); cible_etait_deja_mort = not cible.is_alive; cible.die()
             if not cible_etait_deja_mort and cible.role.name == "Chasseur":
                  if cible not in self.chasseurs_morts_sequence: self.chasseurs_morts_sequence.insert(0, cible)
             self.organiser_cartes_joueurs(); self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 500


    def passer_action_humaine(self):
        if not self.acteur_humain_actuel or not self.action_humaine_attendue: return
        acteur = self.acteur_humain_actuel; action = self.action_humaine_attendue
        if action == "Voyante":
            self.log_message_jeu(f"{acteur.name} (Voyante) passe."); print(f"DEBUG: Humain {acteur.name} passe.")
            self.boutons_jeu["confirmer"].actif = False; self.boutons_jeu["passer"].actif = False; self.cible_humaine_selectionnee = None; self.acteur_humain_actuel = None; self.action_humaine_attendue = None
            for carte in self.cartes_joueurs_visuels: carte.selectionne = False
            self.etat_jeu = ETAT_NUIT_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 200
        else: print(f"WARN: Tentative passer action non passable ({action})")

    def resoudre_nuit(self):
        if not self.jeu or self.jeu.game_over: return
        self.log_message_jeu("\nLe village se réveille..."); morts_cette_nuit = []; cible_loup = self.jeu.killed_this_night[0] if self.jeu.killed_this_night else None
        if cible_loup and cible_loup.is_alive and cible_loup != self.jeu.saved_this_night: morts_cette_nuit.append(cible_loup); self.log_message_jeu(f"{cible_loup.name} dévoré(e) !")
        cible_poison = self.jeu.potioned_to_death_this_night
        if cible_poison and cible_poison.is_alive and cible_poison != self.jeu.saved_this_night and cible_poison not in morts_cette_nuit: morts_cette_nuit.append(cible_poison); self.log_message_jeu(f"{cible_poison.name} empoisonné(e) !")
        chasseurs_morts = [];
        for joueur_mort in morts_cette_nuit:
             if joueur_mort.is_alive: joueur_mort.die();
             if joueur_mort.role.name == "Chasseur": chasseurs_morts.append(joueur_mort)
        self.organiser_cartes_joueurs()
        if chasseurs_morts: self.chasseurs_morts_sequence = chasseurs_morts; self.callback_apres_chasseur = self.verifier_victoire_et_lancer_jour; self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 1000
        else: self.verifier_victoire_et_lancer_jour()

    def executer_action_chasseur_suivante(self):
        if not self.jeu or self.jeu.game_over: self.verifier_victoire_et_lancer_jour(); return
        if not self.chasseurs_morts_sequence:
            if self.callback_apres_chasseur: self.callback_apres_chasseur(); self.callback_apres_chasseur = None; return

        chasseur = self.chasseurs_morts_sequence.pop(0)
        if chasseur.is_alive: print(f"WARN: Chasseur {chasseur.name} listé mais vivant."); self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 50; return

        self.log_message_jeu(f"\nChasseur {chasseur.name} (mort) choisit cible !"); cibles_vivantes = self.jeu.get_alive_players()
        if not cibles_vivantes: self.log_message_jeu("... personne n'est vivant !"); self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 500; return

        if chasseur.is_human: self.preparer_action_humaine(chasseur, "Chasseur"); self.etat_jeu = ETAT_CHASSEUR_ATTENTE_HUMAIN
        else: # IA
             print(f"DEBUG: Chasseur IA {chasseur.name} agit..."); cible_ia = random.choice(cibles_vivantes) if cibles_vivantes else None
             if cible_ia: self.log_message_jeu(f"Chasseur IA {chasseur.name} tire sur {cible_ia.name} !"); cible_etait_deja_mort = not cible_ia.is_alive; cible_ia.die()
             if not cible_etait_deja_mort and cible_ia.role.name == "Chasseur":
                  if cible_ia not in self.chasseurs_morts_sequence: self.chasseurs_morts_sequence.insert(0, cible_ia)
             self.organiser_cartes_joueurs(); self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 1000

    def verifier_victoire_et_lancer_jour(self):
        if self.jeu and self.jeu.check_victory_condition(): self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie()
        else: self.etat_jeu = ETAT_JOUR_DEBAT; self.lancer_phase_jour()

    def lancer_phase_jour(self):
        if not self.jeu or self.jeu.game_over: return
        self.jeu.is_day = True; self.log_message_jeu(f"\n--- Jour {self.jeu.day_count} ---")
        joueurs_vivants = self.jeu.get_alive_players(); self.log_message_jeu(f"Vivants : {', '.join([p.name for p in joueurs_vivants])}")
        if self.jeu.check_victory_condition(): self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie(); return
        humains_vivants = [p for p in joueurs_vivants if p.is_human]
        if len(humains_vivants) > 1: self.log_message_jeu("\nPhase de débat."); self.boutons_jeu["passer_au_vote"].actif = True; self.etat_jeu = ETAT_JOUR_DEBAT
        else: self.log_message_jeu("\nVote..."); self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE; self.lancer_phase_vote()

    def lancer_phase_vote(self):
        if not self.jeu or self.jeu.game_over: return
        self.boutons_jeu["passer_au_vote"].actif = False; self.log_message_jeu("\n--- Phase de Vote ---")
        self.votants_restants = self.jeu.get_alive_players(); self.votes_en_cours = {}
        self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 500

    def traiter_votant_suivant(self):
        if not self.jeu or self.jeu.game_over: self.verifier_victoire_et_lancer_nuit(); return
        # Traiter vote humain précédent s'il y en a un
        if self._human_vote_target is not None:
             voter_prec = self.game.get_player_by_name(self._human_vote_target_actor_name) if self._human_vote_target_actor_name else None
             if voter_prec and self._human_vote_target.is_alive:
                  target = self._human_vote_target; self.votes_en_cours[target] = self.votes_en_cours.get(target, 0) + 1; print(f"DEBUG: Vote humain {voter_prec.name} -> {target.name} enregistré.")
             elif voter_prec: self.log_message_jeu(f"{voter_prec.name} vote annulé (cible morte).")
             self._human_vote_target = None; self._human_vote_target_actor_name = None

        if not self.votants_restants: self.etat_jeu = ETAT_JOUR_VOTE_RESOLUTION; self.delai_prochaine_action = pygame.time.get_ticks() + 500; return

        votant = self.votants_restants.pop(0)
        if not votant.is_alive: print(f"DEBUG: Vote - {votant.name} mort, skip."); self.delai_prochaine_action = pygame.time.get_ticks() + 50; self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE; return

        if votant.is_human: self.preparer_action_humaine(votant, "Vote"); self.etat_jeu = ETAT_JOUR_VOTE_ATTENTE_HUMAIN
        else: # IA
             if hasattr(votant, 'ai_logic') and votant.ai_logic:
                  cible_ia = votant.ai_logic.decide_vote();
                  if cible_ia and cible_ia.is_alive: self.votes_en_cours[cible_ia] = self.votes_en_cours.get(cible_ia, 0) + 1; print(f"DEBUG: Vote IA - {votant.name} -> {cible_ia.name}")
                  else: print(f"DEBUG: Vote IA - {votant.name} vote invalide.")
             else: print(f"ERREUR: IA {votant.name} sans ai_logic.");
             self.delai_prochaine_action = pygame.time.get_ticks() + 300; self.etat_jeu = ETAT_JOUR_VOTE_SEQUENCE

    def resoudre_vote(self):
        if not self.jeu or self.jeu.game_over: return
        self.log_message_jeu("\n--- Résultat du Vote ---"); lynche_joueur = None
        if not self.votes_en_cours: self.log_message_jeu("Aucun vote.")
        else:
            vivants_tries = sorted(self.jeu.get_alive_players(), key=lambda p: p.name)
            for p in vivants_tries: self.log_message_jeu(f"- {p.name}: {self.votes_en_cours.get(p, 0)} voix")
            max_votes = 0;
            for count in self.votes_en_cours.values(): max_votes = max(max_votes, count)
            candidats = [p for p, count in self.votes_en_cours.items() if count == max_votes]
            if max_votes == 0: self.log_message_jeu("Personne n'a reçu de vote.")
            elif len(candidats) > 1: self.log_message_jeu(f"Égalité: {', '.join([p.name for p in candidats])}"); lynche_joueur = random.choice(candidats); self.log_message_jeu(f"Tirage: {lynche_joueur.name} lynché(e) !")
            else: lynche_joueur = candidats[0]; self.log_message_jeu(f"{lynche_joueur.name} lynché(e) avec {max_votes} voix !")

        if lynche_joueur and lynche_joueur.is_alive:
             joueur_mort = lynche_joueur; joueur_mort.die(); self.log_message_jeu(f"Son rôle : {joueur_mort.role.name}"); self.organiser_cartes_joueurs()
             if joueur_mort.role.name == "Chasseur": self.chasseurs_morts_sequence = [joueur_mort]; self.callback_apres_chasseur = self.verifier_victoire_et_lancer_nuit; self.etat_jeu = ETAT_CHASSEUR_SEQUENCE; self.delai_prochaine_action = pygame.time.get_ticks() + 1000
             else: self.verifier_victoire_et_lancer_nuit()
        else: self.log_message_jeu("Personne éliminé."); self.verifier_victoire_et_lancer_nuit()

    def verifier_victoire_et_lancer_nuit(self):
        if self.jeu and self.jeu.check_victory_condition(): self.etat_jeu = ETAT_FIN_PARTIE; self.preparer_fin_partie()
        else: self.etat_jeu = ETAT_NUIT_SEQUENCE; self.lancer_phase_nuit()

    def preparer_fin_partie(self):
        if not self.jeu: return; self.log_message_jeu("\n--- PARTIE TERMINEE ---"); self.jeu.game_over = True
        self.jeu.check_victory_condition(); gagnant = self.jeu.winning_team if self.jeu.winning_team else "Indetermine"; self.log_message_jeu(f"Gagnants : {gagnant}")
        self.log_message_jeu("\nRôles finaux :");
        for p in self.jeu.players: statut = "Vivant" if p.is_alive else "Mort"; self.log_message_jeu(f"- {p.name}: {p.role.name} ({statut})")
        self.boutons_jeu["nouvelle_partie"].actif = True; self.boutons_jeu["quitter"].actif = True; self.boutons_jeu["confirmer"].actif = False; self.boutons_jeu["passer"].actif = False; self.boutons_jeu["passer_au_vote"].actif = False
        for carte in self.cartes_joueurs_visuels: carte.afficher_role = True

    def reinitialiser_jeu(self):
        self.jeu = None; self.etat_jeu = ETAT_CONFIG; self.log_messages_jeu = []; self.cartes_joueurs_visuels = []
        for btn in self.boutons_jeu.values(): btn.actif = False
        self.widgets_config["bouton_demarrer"].actif = True
        self.log_message_jeu("Retour configuration.") # Log pour console


# --- Lancement ---
if __name__ == '__main__':
    app = GameApp()
    if app.en_cours: # Vérifier si l'init a réussi
        app.run()