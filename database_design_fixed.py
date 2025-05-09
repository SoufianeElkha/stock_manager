"""
Module de gestion de la base de données pour le gestionnaire de stock
"""

import os
import sqlite3
from datetime import datetime

class DatabaseManager:
    """Gestionnaire de base de données pour le stockage des articles et des mouvements"""
    
    def __init__(self, db_file="data/stock_database.db"):
        """Initialise le gestionnaire avec le chemin du fichier de base de données"""
        self.db_file = db_file
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Établit une connexion à la base de données"""
        # Créer le répertoire data s'il n'existe pas
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        
        # Établir la connexion
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        print("Connexion à la base de données établie avec succès")
        return True
    
    def create_tables(self):
        """Crée les tables nécessaires si elles n'existent pas"""
        # Créer la table des articles
        self.cursor.execute('''
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
        
        # Créer la table des mouvements
        self.cursor.execute('''
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
        
        self.conn.commit()
        print("Tables créées avec succès")
        return True
    
    def migrate_old_database(self):
        """Migre l'ancienne structure de base de données vers la nouvelle si nécessaire"""
        try:
            # Vérifier si la colonne position existe
            self.cursor.execute("PRAGMA table_info(articles)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            # Ajouter la colonne position si elle n'existe pas
            if "position" not in columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN position TEXT")
                self.conn.commit()
            
            # Ajouter la colonne quantite_minimale si elle n'existe pas
            if "quantite_minimale" not in columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN quantite_minimale INTEGER DEFAULT 0")
                self.conn.commit()
            
            # Vérifier si la colonne date_creation existe
            if "date_creation" not in columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                self.conn.commit()
            
            # Vérifier si la colonne date_modification existe
            if "date_modification" not in columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                self.conn.commit()
            
            # Vérifier la structure de la table mouvements
            self.cursor.execute("PRAGMA table_info(mouvements)")
            mouvement_columns = [column[1] for column in self.cursor.fetchall()]
            
            # Vérifier si la table mouvements existe
            if not mouvement_columns:
                self.create_tables()
                return True
            
            # Vérifier si la colonne type_mouvement existe
            if "type_mouvement" not in mouvement_columns:
                self.cursor.execute("ALTER TABLE mouvements ADD COLUMN type_mouvement TEXT")
                self.conn.commit()
            
            # Vérifier si la colonne projet existe
            if "projet" not in mouvement_columns and "commentaire" in mouvement_columns:
                # Renommer la colonne commentaire en projet
                self.cursor.execute('''
                CREATE TABLE mouvements_new (
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
                
                self.cursor.execute('''
                INSERT INTO mouvements_new (id, article_reference, date_mouvement, type_mouvement, quantite, projet, travailleur)
                SELECT id, article_id, date_mouvement, type_mouvement, quantite, commentaire, travailleur FROM mouvements
                ''')
                
                self.cursor.execute("DROP TABLE mouvements")
                self.cursor.execute("ALTER TABLE mouvements_new RENAME TO mouvements")
                self.conn.commit()
            
            # Vérifier si la colonne travailleur existe
            if "travailleur" not in mouvement_columns:
                self.cursor.execute("ALTER TABLE mouvements ADD COLUMN travailleur TEXT")
                self.conn.commit()
            
            return True
        
        except Exception as e:
            print(f"Erreur lors de la migration de la base de données: {e}")
            return False
    
    def add_article(self, reference, description, quantite=0, quantite_minimale=0, position=""):
        """
        Ajoute un nouvel article à la base de données
        
        Args:
            reference: Référence unique de l'article
            description: Description de l'article
            quantite: Quantité initiale (défaut: 0)
            quantite_minimale: Quantité minimale pour alerte (défaut: 0)
            position: Position de l'article dans le stock (défaut: "")
            
        Returns:
            bool: True si l'ajout a réussi, False sinon
        """
        try:
            # Date actuelle
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Insérer l'article
            self.cursor.execute("""
            INSERT INTO articles (reference, description, quantite, quantite_minimale, position, date_creation, date_modification)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (reference, description, quantite, quantite_minimale, position, current_date, current_date))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de l'ajout de l'article: {e}")
            return False
    
    def update_article(self, reference, description, quantite_minimale=None, position=None):
        """
        Met à jour les informations d'un article existant
        
        Args:
            reference: Référence de l'article à mettre à jour
            description: Nouvelle description
            quantite_minimale: Nouvelle quantité minimale (optionnel)
            position: Nouvelle position (optionnel)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Récupérer les valeurs actuelles
            self.cursor.execute("SELECT quantite_minimale, position FROM articles WHERE reference = ?", (reference,))
            result = self.cursor.fetchone()
            
            if not result:
                return False
            
            current_min_qty, current_position = result
            
            # Utiliser les valeurs actuelles si non spécifiées
            if quantite_minimale is None:
                quantite_minimale = current_min_qty
            
            if position is None:
                position = current_position
            
            # Date actuelle
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Mettre à jour l'article
            self.cursor.execute("""
            UPDATE articles
            SET description = ?, quantite_minimale = ?, position = ?, date_modification = ?
            WHERE reference = ?
            """, (description, quantite_minimale, position, current_date, reference))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'article: {e}")
            return False
    
    def update_quantity(self, reference, quantite, type_mouvement, projet=None, travailleur=None):
        """
        Met à jour la quantité d'un article et enregistre le mouvement
        
        Args:
            reference: Référence de l'article
            quantite: Quantité à ajouter ou retirer (doit être positive)
            type_mouvement: Type de mouvement ("AJOUT" ou "RETRAIT")
            projet: Projet associé au mouvement (optionnel)
            travailleur: Nom du travailleur (optionnel)
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Vérifier que la quantité est positive
            if quantite <= 0:
                print("La quantité doit être positive")
                return False
            
            # Récupérer la quantité actuelle
            self.cursor.execute("SELECT quantite FROM articles WHERE reference = ?", (reference,))
            result = self.cursor.fetchone()
            
            if not result:
                print(f"Article non trouvé: {reference}")
                return False
            
            current_quantity = result[0]
            
            # Calculer la nouvelle quantité
            if type_mouvement == "AJOUT":
                new_quantity = current_quantity + quantite
            elif type_mouvement == "RETRAIT":
                if current_quantity < quantite:
                    print(f"Quantité insuffisante. Stock actuel: {current_quantity}")
                    raise ValueError(f"Quantité insuffisante. Stock actuel: {current_quantity}")
                new_quantity = current_quantity - quantite
            else:
                print(f"Type de mouvement non reconnu: {type_mouvement}")
                return False
            
            # Mettre à jour la quantité
            self.cursor.execute("""
            UPDATE articles
            SET quantite = ?, date_modification = datetime('now', 'localtime')
            WHERE reference = ?
            """, (new_quantity, reference))
            
            # Enregistrer le mouvement
            self.cursor.execute("""
            INSERT INTO mouvements (article_reference, type_mouvement, quantite, projet, travailleur)
            VALUES (?, ?, ?, ?, ?)
            """, (reference, type_mouvement, quantite, projet, travailleur))
            
            self.conn.commit()
            return True
        except ValueError as e:
            # Propager l'erreur pour les tests
            raise e
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la quantité: {e}")
            return False
    
    def delete_article(self, reference):
        """
        Supprime un article et ses mouvements associés
        
        Args:
            reference: Référence de l'article à supprimer
            
        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        try:
            # Supprimer les mouvements associés
            self.cursor.execute("DELETE FROM mouvements WHERE article_reference = ?", (reference,))
            
            # Supprimer l'article
            self.cursor.execute("DELETE FROM articles WHERE reference = ?", (reference,))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de la suppression de l'article: {e}")
            return False
    
    def get_article(self, reference):
        """
        Récupère les informations d'un article
        
        Args:
            reference: Référence de l'article
            
        Returns:
            tuple: Informations de l'article ou None si non trouvé
        """
        try:
            self.cursor.execute("""
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification
            FROM articles
            WHERE reference = ?
            """, (reference,))
            
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Erreur lors de la récupération de l'article: {e}")
            return None
    
    def get_all_articles(self):
        """
        Récupère tous les articles
        
        Returns:
            list: Liste des articles
        """
        try:
            self.cursor.execute("""
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification
            FROM articles
            ORDER BY reference
            """)
            
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des articles: {e}")
            return []
    
    def search_articles(self, search_term):
        """
        Recherche des articles par référence ou description
        
        Args:
            search_term: Terme de recherche
            
        Returns:
            list: Liste des articles correspondants
        """
        try:
            search_term = f"%{search_term}%"
            
            self.cursor.execute("""
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification
            FROM articles
            WHERE reference LIKE ? OR description LIKE ?
            ORDER BY reference
            """, (search_term, search_term))
            
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la recherche d'articles: {e}")
            return []
    
    def get_article_movements(self, reference):
        """
        Récupère les mouvements d'un article
        
        Args:
            reference: Référence de l'article
            
        Returns:
            list: Liste des mouvements
        """
        try:
            self.cursor.execute("""
            SELECT id, article_reference, date_mouvement, type_mouvement, quantite, projet, travailleur
            FROM mouvements
            WHERE article_reference = ?
            ORDER BY date_mouvement DESC
            """, (reference,))
            
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des mouvements: {e}")
            return []
    
    def get_low_stock_articles(self, threshold=None):
        """
        Récupère les articles dont la quantité est inférieure à la quantité minimale
        
        Args:
            threshold: Seuil personnalisé (optionnel)
            
        Returns:
            list: Liste des articles à stock bas
        """
        try:
            if threshold is not None:
                self.cursor.execute("""
                SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification
                FROM articles
                WHERE quantite < ?
                ORDER BY reference
                """, (threshold,))
            else:
                self.cursor.execute("""
                SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification
                FROM articles
                WHERE quantite < quantite_minimale
                ORDER BY reference
                """)
            
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des articles à stock bas: {e}")
            return []
    
    def export_data_for_external_db(self):
        """
        Exporte les données pour une base de données externe
        
        Returns:
            tuple: (articles, mouvements) contenant les données à exporter
        """
        try:
            # Récupérer tous les articles
            self.cursor.execute("""
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification
            FROM articles
            """)
            articles = self.cursor.fetchall()
            
            # Récupérer tous les mouvements
            self.cursor.execute("""
            SELECT id, article_reference, date_mouvement, type_mouvement, quantite, projet, travailleur
            FROM mouvements
            """)
            mouvements = self.cursor.fetchall()
            
            return articles, mouvements
        except Exception as e:
            print(f"Erreur lors de l'exportation des données: {e}")
            return [], []
    
    def close(self):
        """Ferme la connexion à la base de données"""
        if self.conn:
            self.conn.close()
            print("Connexion à la base de données fermée")
            return True
        return False
