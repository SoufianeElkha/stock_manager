"""
Module principal modifié pour intégrer les nouvelles fonctionnalités
- Sélection de l'emplacement de la base de données au premier lancement
- Système de sauvegarde automatique quotidienne
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

# Importer les modules de l'application
from database_design import DatabaseManager
from stock_functions import StockManager
from gui_interface import ModernStockManagerApp
from db_location_manager import DatabaseLocationManager
from backup_manager import BackupManager

def main():
    """Fonction principale de l'application"""
    # Initialiser la fenêtre principale
    root = tk.Tk()
    root.title("Gestionnaire de Stock Swisspro")
    
    # Configurer l'emplacement de la base de données
    db_manager = DatabaseLocationManager()
    success, db_path = db_manager.setup_database_location()
    
    if not success or not db_path:
        messagebox.showerror(
            "Erreur de configuration",
            "Impossible de configurer l'emplacement de la base de données.\n"
            "L'application va utiliser l'emplacement par défaut."
        )
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stock_database.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Initialiser le gestionnaire de sauvegarde
    backup_mgr = BackupManager(db_path)
    
    # Démarrer la sauvegarde automatique
    backup_mgr.start_automatic_backup()
    
    # Créer une sauvegarde au démarrage
    current_date = datetime.now().strftime("%Y-%m-%d")
    last_backup = None
    
    if backup_mgr.last_backup_date:
        last_backup = backup_mgr.last_backup_date.strftime("%Y-%m-%d")
    
    # Si aucune sauvegarde n'a été faite aujourd'hui, en créer une
    if last_backup != current_date:
        success, message, _ = backup_mgr.create_backup()
        if not success:
            print(f"Erreur lors de la création de la sauvegarde au démarrage: {message}")
    
    # Initialiser l'application
    app = ModernStockManagerApp(root, db_path)
    
    # Configurer la fermeture de l'application
    def on_closing():
        """Fonction appelée lors de la fermeture de l'application"""
        # Arrêter la sauvegarde automatique
        backup_mgr.stop_automatic_backup()
        
        # Fermer l'application
        root.destroy()
    
    # Associer la fonction à l'événement de fermeture
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Démarrer la boucle principale
    root.mainloop()

if __name__ == "__main__":
    main()
