"""
Module pour la compatibilité avec une base de données externe
"""

import os
import json
import sqlite3
import configparser
import threading
import time
from pathlib import Path

class ExternalDatabaseConnector:
    """Connecteur pour une base de données externe"""
    
    def __init__(self, config_file="config/db_config.ini"):
        """
        Initialise le connecteur avec un fichier de configuration
        
        Le fichier de configuration doit contenir les informations de connexion
        à la base de données externe (chemin du fichier ou paramètres de connexion réseau)
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.external_db_path = None
        self.db_path = None  # Ajout de l'attribut db_path pour compatibilité
        self.sync_interval = 60  # Intervalle de synchronisation en secondes
        self.sync_thread = None
        self.stop_sync = threading.Event()
        
        # Créer le répertoire de configuration s'il n'existe pas
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        # Charger la configuration ou créer un fichier par défaut
        if os.path.exists(config_file):
            self.load_config()
        else:
            self.create_default_config()
    
    def create_default_config(self):
        """Crée un fichier de configuration par défaut"""
        self.config['DATABASE'] = {
            'Type': 'file',  # 'file' ou 'network'
            'Path': 'data/external_db.sqlite',  # Chemin pour une base de données fichier
            'Host': 'localhost',  # Hôte pour une base de données réseau
            'Port': '5432',  # Port pour une base de données réseau
            'Name': 'stock_db',  # Nom de la base de données
            'User': 'user',  # Utilisateur
            'Password': 'password',  # Mot de passe
            'SyncInterval': '60'  # Intervalle de synchronisation en secondes
        }
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        
        # Définir le chemin de la base de données externe
        self.external_db_path = self.config['DATABASE']['Path']
        self.db_path = self.external_db_path  # Synchroniser les deux attributs
        self.sync_interval = int(self.config['DATABASE']['SyncInterval'])
    
    def load_config(self):
        """Charge la configuration depuis le fichier"""
        self.config.read(self.config_file)
        
        # Définir le chemin de la base de données externe
        if self.config['DATABASE']['Type'] == 'file':
            self.external_db_path = self.config['DATABASE']['Path']
        else:
            # Pour une base de données réseau, on utiliserait une chaîne de connexion
            # Mais pour simplifier, on utilise un fichier local
            self.external_db_path = 'data/external_db.sqlite'
        
        # Synchroniser les deux attributs
        self.db_path = self.external_db_path
        self.sync_interval = int(self.config['DATABASE']['SyncInterval'])
    
    def save_config(self):
        """Enregistre la configuration dans le fichier"""
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def update_config(self, section, key, value):
        """Met à jour une valeur dans la configuration"""
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = str(value)
        self.save_config()
        
        # Mettre à jour les variables internes si nécessaire
        if section == 'DATABASE':
            if key == 'Path' and self.config['DATABASE']['Type'] == 'file':
                self.external_db_path = value
                self.db_path = value  # Synchroniser les deux attributs
            elif key == 'SyncInterval':
                self.sync_interval = int(value)
    
    def initialize_external_db(self):
        """Initialise la base de données externe"""
        try:
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(self.external_db_path), exist_ok=True)
            
            # Créer la connexion à la base de données externe
            conn = sqlite3.connect(self.external_db_path)
            cursor = conn.cursor()
            
            # Créer les tables nécessaires
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                reference TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                quantite INTEGER NOT NULL DEFAULT 0,
                quantite_minimale INTEGER NOT NULL DEFAULT 0,
                position TEXT,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mouvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_reference TEXT NOT NULL,
                date_mouvement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                type_mouvement TEXT NOT NULL,
                quantite INTEGER NOT NULL,
                projet TEXT,
                travailleur TEXT,
                FOREIGN KEY (article_reference) REFERENCES articles (reference)
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                operation TEXT NOT NULL,
                details TEXT
            )
            ''')
            
            conn.commit()
            conn.close()
            
            print(f"Base de données externe initialisée: {self.external_db_path}")
            return True
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la base externe: {e}")
            return False
    
    def export_to_external_db(self, db_manager):
        """
        Exporte les données de la base locale vers la base externe
        
        Args:
            db_manager: Instance de DatabaseManager contenant les données à exporter
            
        Returns:
            bool: True si l'exportation a réussi, False sinon
        """
        try:
            # Vérifier que la base externe existe
            if not os.path.exists(self.external_db_path):
                self.initialize_external_db()
            
            # Récupérer les données à exporter
            articles, mouvements = db_manager.export_data_for_external_db()
            
            # Connexion à la base externe
            conn = sqlite3.connect(self.external_db_path)
            cursor = conn.cursor()
            
            # Vider les tables existantes
            cursor.execute("DELETE FROM mouvements")
            cursor.execute("DELETE FROM articles")
            
            # Insérer les articles
            for article in articles:
                cursor.execute("""
                INSERT INTO articles (reference, description, quantite, quantite_minimale, position, date_creation, date_modification)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, article)
            
            # Insérer les mouvements
            for mouvement in mouvements:
                cursor.execute("""
                INSERT INTO mouvements (id, article_reference, date_mouvement, type_mouvement, quantite, projet, travailleur)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, mouvement)
            
            # Valider les changements
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Erreur lors de l'exportation vers la base externe: {e}")
            return False
    
    def import_to_local_db(self, local_db_manager):
        """
        Importe les données de la base externe vers la base locale
        
        Args:
            local_db_manager: Instance de DatabaseManager pour la base locale
            
        Returns:
            bool: True si l'importation a réussi, False sinon
        """
        try:
            # Vérifier si la base externe existe
            if not os.path.exists(self.external_db_path):
                print(f"La base externe n'existe pas: {self.external_db_path}")
                return False
            
            # Connexion à la base externe
            ext_conn = sqlite3.connect(self.external_db_path)
            ext_cursor = ext_conn.cursor()
            
            # Récupérer les articles
            ext_cursor.execute("""
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification 
            FROM articles
            """)
            articles = ext_cursor.fetchall()
            
            # Récupérer les mouvements
            ext_cursor.execute("""
            SELECT id, article_reference, date_mouvement, type_mouvement, quantite, projet, travailleur 
            FROM mouvements
            """)
            mouvements = ext_cursor.fetchall()
            
            ext_conn.close()
            
            # Désactiver les contraintes de clé étrangère temporairement
            local_db_manager.cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Commencer une transaction
            local_db_manager.conn.execute("BEGIN TRANSACTION")
            
            try:
                # Vider les tables existantes
                local_db_manager.cursor.execute("DELETE FROM mouvements")
                local_db_manager.cursor.execute("DELETE FROM articles")
                
                # Réinitialiser les compteurs d'auto-incrémentation
                local_db_manager.cursor.execute("DELETE FROM sqlite_sequence WHERE name='mouvements'")
                
                # Insérer les articles
                for article in articles:
                    local_db_manager.cursor.execute('''
                    INSERT INTO articles (reference, description, quantite, quantite_minimale, position, date_creation, date_modification)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', article)
                
                # Insérer les mouvements
                for mouvement in mouvements:
                    local_db_manager.cursor.execute('''
                    INSERT INTO mouvements (id, article_reference, date_mouvement, type_mouvement, quantite, projet, travailleur)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', mouvement)
                
                # Valider la transaction
                local_db_manager.conn.commit()
                
                print(f"Données importées avec succès depuis {self.external_db_path}")
                return True
            
            except Exception as e:
                # Annuler la transaction en cas d'erreur
                local_db_manager.conn.rollback()
                print(f"Erreur lors de l'importation des données: {e}")
                return False
            
            finally:
                # Réactiver les contraintes de clé étrangère
                local_db_manager.cursor.execute("PRAGMA foreign_keys = ON")
        
        except Exception as e:
            print(f"Erreur lors de la connexion à la base externe: {e}")
            return False
    
    # Alias pour compatibilité avec l'ancienne méthode
    import_from_external_db = import_to_local_db
    
    def start_sync_thread(self, local_db_manager):
        """
        Démarre un thread pour synchroniser périodiquement les données
        
        Args:
            local_db_manager: Instance de DatabaseManager pour la base locale
        """
        if self.sync_thread and self.sync_thread.is_alive():
            print("Le thread de synchronisation est déjà en cours d'exécution")
            return
        
        self.stop_sync.clear()
        self.sync_thread = threading.Thread(
            target=self._sync_thread_function,
            args=(local_db_manager,),
            daemon=True
        )
        self.sync_thread.start()
        print(f"Thread de synchronisation démarré (intervalle: {self.sync_interval} secondes)")
    
    def stop_sync_thread(self):
        """Arrête le thread de synchronisation"""
        if self.sync_thread and self.sync_thread.is_alive():
            self.stop_sync.set()
            self.sync_thread.join(timeout=2)
            print("Thread de synchronisation arrêté")
    
    def _sync_thread_function(self, local_db_manager):
        """Fonction exécutée par le thread de synchronisation"""
        while not self.stop_sync.is_set():
            try:
                print(f"Synchronisation en cours... ({time.strftime('%H:%M:%S')})")
                
                # Exporter les données vers la base externe
                self.export_to_external_db(local_db_manager)
                
                # Attendre l'intervalle de synchronisation
                for _ in range(self.sync_interval):
                    if self.stop_sync.is_set():
                        break
                    time.sleep(1)
            
            except Exception as e:
                print(f"Erreur dans le thread de synchronisation: {e}")
                time.sleep(10)  # Attendre un peu en cas d'erreur
    
    def export_config_to_json(self, output_file="config/db_config.json"):
        """
        Exporte la configuration au format JSON
        
        Args:
            output_file: Chemin du fichier JSON de sortie
            
        Returns:
            bool: True si l'exportation a réussi, False sinon
        """
        try:
            # Convertir la configuration en dictionnaire
            config_dict = {section: dict(self.config[section]) for section in self.config.sections()}
            
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Écrire le fichier JSON
            with open(output_file, 'w') as f:
                json.dump(config_dict, f, indent=4)
            
            print(f"Configuration exportée vers {output_file}")
            return True
        
        except Exception as e:
            print(f"Erreur lors de l'exportation de la configuration: {e}")
            return False
    
    def import_config_from_json(self, input_file="config/db_config.json"):
        """
        Importe la configuration depuis un fichier JSON
        
        Args:
            input_file: Chemin du fichier JSON d'entrée
            
        Returns:
            bool: True si l'importation a réussi, False sinon
        """
        try:
            # Vérifier si le fichier existe
            if not os.path.exists(input_file):
                print(f"Le fichier de configuration n'existe pas: {input_file}")
                return False
            
            # Lire le fichier JSON
            with open(input_file, 'r') as f:
                config_dict = json.load(f)
            
            # Mettre à jour la configuration
            for section, options in config_dict.items():
                if section not in self.config:
                    self.config[section] = {}
                
                for key, value in options.items():
                    self.config[section][key] = value
            
            # Enregistrer la configuration
            self.save_config()
            
            # Mettre à jour les variables internes
            self.load_config()
            
            print(f"Configuration importée depuis {input_file}")
            return True
        
        except Exception as e:
            print(f"Erreur lors de l'importation de la configuration: {e}")
            return False
