import tkinter as tk
from gui import GameGUI # Importer la classe GUI

def main():
    root = tk.Tk() # Crée la fenêtre principale Tkinter
    app = GameGUI(root) # Crée une instance de votre application GUI
    root.mainloop() # Lance la boucle principale d'événements Tkinter

if __name__ == "__main__":
    main()