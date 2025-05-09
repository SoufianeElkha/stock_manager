"""
Module de configuration de l'emplacement de la base de données
Ce module permet à l'utilisateur de spécifier l'emplacement de la base de données au premier lancement
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import configparser
import sqlite3
from pathlib import Path

class DatabaseLocationManager:
    """Gestionnaire de l'emplacement de la base de données"""
    
    def __init__(self, config_file=None):
        """
        Initialise le gestionnaire d'emplacement de la base de données
        
        Args:
            config_file: Chemin du fichier de configuration (optionnel)
        """
        # Définir le fichier de configuration
        self.config_file = config_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "config", 
            "database_config.ini"
        )
        
        # Créer le répertoire de configuration s'il n'existe pas
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Initialiser le parser de configuration
        self.config = configparser.ConfigParser()
        
        # Charger la configuration existante si elle existe
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        
        # Créer la section DATABASE si elle n'existe pas
        if not self.config.has_section('DATABASE'):
            self.config.add_section('DATABASE')
    
    def get_database_path(self):
        """
        Récupère le chemin de la base de données depuis la configuration
        
        Returns:
            str: Chemin de la base de données ou None si non défini
        """
        if self.config.has_option('DATABASE', 'Path'):
            return self.config.get('DATABASE', 'Path')
        return None
    
    def set_database_path(self, db_path):
        """
        Définit le chemin de la base de données dans la configuration
        
        Args:
            db_path: Chemin de la base de données
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Mettre à jour la configuration
            self.config.set('DATABASE', 'Path', db_path)
            
            # Sauvegarder la configuration
            with open(self.config_file, 'w') as configfile:
                self.config.write(configfile)
            
            return True
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la configuration: {e}")
            return False
    
    def is_first_launch(self):
        """
        Vérifie s'il s'agit du premier lancement de l'application
        
        Returns:
            bool: True si c'est le premier lancement, False sinon
        """
        # Vérifier si le fichier de configuration existe
        if not os.path.exists(self.config_file):
            return True
        
        # Vérifier si le chemin de la base de données est défini
        if not self.get_database_path():
            return True
        
        # Vérifier si la base de données existe
        db_path = self.get_database_path()
        if not os.path.exists(db_path):
            return True
        
        return False
    
    def prompt_for_database_location(self):
        """
        Affiche une boîte de dialogue pour demander l'emplacement de la base de données
        
        Returns:
            str: Chemin de la base de données sélectionné ou None si annulé
        """
        # Créer une fenêtre Tkinter
        root = tk.Tk()
        root.withdraw()  # Cacher la fenêtre principale
        
        # Afficher un message d'information
        messagebox.showinfo(
            "Configuration de la base de données",
            "Bienvenue dans le Gestionnaire de Stock Swisspro!\n\n"
            "Veuillez sélectionner l'emplacement où vous souhaitez stocker la base de données."
        )
        
        # Ouvrir la boîte de dialogue pour sélectionner un répertoire
        directory = filedialog.askdirectory(
            title="Sélectionner l'emplacement de la base de données",
            mustexist=True
        )
        
        # Si l'utilisateur a annulé, retourner None
        if not directory:
            return None
        
        # Construire le chemin complet de la base de données
        db_path = os.path.join(directory, "stock_database.db")
        
        # Demander confirmation
        confirm = messagebox.askyesno(
            "Confirmation",
            f"La base de données sera créée à l'emplacement suivant:\n\n{db_path}\n\nConfirmez-vous ce choix?"
        )
        
        # Fermer la fenêtre Tkinter
        root.destroy()
        
        # Retourner le chemin si confirmé, sinon None
        return db_path if confirm else None
    
    def initialize_database(self, db_path):
        """
        Initialise une nouvelle base de données à l'emplacement spécifié
        
        Args:
            db_path: Chemin de la base de données à initialiser
            
        Returns:
            bool: True si l'initialisation a réussi, False sinon
        """
        try:
            # Créer le répertoire parent s'il n'existe pas
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Créer une connexion à la base de données
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Créer les tables nécessaires
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                reference TEXT PRIMARY KEY,
                description TEXT,
                quantite INTEGER,
                position TEXT,
                quantite_minimale INTEGER,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mouvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_reference TEXT,
                date_mouvement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type_mouvement TEXT,
                quantite INTEGER,
                projet TEXT,
                travailleur TEXT,
                FOREIGN KEY (article_reference) REFERENCES articles (reference)
            )
            ''')
            
            # Valider les changements
            conn.commit()
            
            # Fermer la connexion
            conn.close()
            
            return True
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la base de données: {e}")
            return False
    
    def setup_database_location(self):
        """
        Configure l'emplacement de la base de données au premier lancement
        
        Returns:
            tuple: (success, db_path)
                success: True si la configuration a réussi, False sinon
                db_path: Chemin de la base de données configuré ou None
        """
        # Vérifier s'il s'agit du premier lancement
        if not self.is_first_launch():
            return True, self.get_database_path()
        
        # Demander l'emplacement de la base de données
        db_path = self.prompt_for_database_location()
        
        # Si l'utilisateur a annulé, utiliser l'emplacement par défaut
        if not db_path:
            default_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "data",
                "stock_database.db"
            )
            
            # Créer le répertoire data s'il n'existe pas
            os.makedirs(os.path.dirname(default_path), exist_ok=True)
            
            db_path = default_path
        
        # Initialiser la base de données
        if not os.path.exists(db_path):
            success = self.initialize_database(db_path)
            if not success:
                return False, None
        
        # Mettre à jour la configuration
        success = self.set_database_path(db_path)
        
        return success, db_path

def get_database_path():
    """
    Fonction utilitaire pour obtenir le chemin de la base de données
    
    Returns:
        str: Chemin de la base de données configuré
    """
    db_manager = DatabaseLocationManager()
    
    # Si c'est le premier lancement, configurer l'emplacement
    if db_manager.is_first_launch():
        success, db_path = db_manager.setup_database_location()
        if not success:
            # En cas d'échec, utiliser l'emplacement par défaut
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "data",
                "stock_database.db"
            )
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
    else:
        # Sinon, récupérer l'emplacement configuré
        db_path = db_manager.get_database_path()
    
    return db_path

if __name__ == "__main__":
    # Si exécuté directement, configurer l'emplacement de la base de données
    db_manager = DatabaseLocationManager()
    success, db_path = db_manager.setup_database_location()
    
    if success:
        print(f"Base de données configurée avec succès: {db_path}")
        sys.exit(0)
    else:
        print("Échec de la configuration de la base de données")
        sys.exit(1)
