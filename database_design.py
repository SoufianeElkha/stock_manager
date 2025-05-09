"""
Module de gestion de la base de données pour le gestionnaire de stock
"""

import os
import sqlite3
from datetime import datetime
import hashlib # Ajout pour le hachage du PIN

class DatabaseManager:
    """Gestionnaire de base de données pour le stockage des articles, des mouvements et des utilisateurs"""
    
    def __init__(self, db_file="data/stock_database.db"):
        """Initialise le gestionnaire avec le chemin du fichier de base de données"""
        self.db_file = db_file
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Établit une connexion à la base de données"""
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        self.conn = sqlite3.connect(self.db_file)
        self.cursor = self.conn.cursor()
        # Activer les clés étrangères
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        print("Connexion à la base de données établie avec succès")
        return True
    
    def create_tables(self):
        """Crée les tables nécessaires si elles n'existent pas"""
        # Créer la table des utilisateurs
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_utilisateur TEXT UNIQUE NOT NULL,
            pin_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'utilisateur')),
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Créer la table des articles
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            reference TEXT PRIMARY KEY,
            description TEXT,
            quantite INTEGER,
            position TEXT,
            quantite_minimale INTEGER,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            derniere_notification_envoyee TIMESTAMP NULL
        )
        ''')
        
        # Créer la table des mouvements
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS mouvements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_reference TEXT NOT NULL,
            id_utilisateur INTEGER NULL, -- Peut être NULL pour les actions système ou avant l'implémentation de l'auth
            date_mouvement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            type_mouvement TEXT NOT NULL, -- Ex: 'AJOUT_STOCK', 'RETRAIT_STOCK', 'CREATION_ARTICLE', etc.
            quantite_avant_mouvement INTEGER NOT NULL,
            quantite_apres_mouvement INTEGER NOT NULL,
            quantite_change INTEGER NOT NULL, -- Quantité ajoutée ou retirée (positive pour ajout, négative pour retrait)
            projet TEXT,
            travailleur TEXT, -- Ce champ pourrait être lié à id_utilisateur ou rester pour une information contextuelle
            FOREIGN KEY (article_reference) REFERENCES articles (reference) ON DELETE CASCADE,
            FOREIGN KEY (id_utilisateur) REFERENCES utilisateurs (id) ON DELETE SET NULL
        )
        ''')
        
        self.conn.commit()
        print("Tables (utilisateurs, articles, mouvements) créées ou vérifiées avec succès")
        return True

    def _hash_pin(self, pin):
        """Hashe un PIN en utilisant SHA256."""
        return hashlib.sha256(pin.encode()).hexdigest()

    def add_user(self, nom_utilisateur, pin, role='utilisateur'):
        """Ajoute un nouvel utilisateur à la base de données."""
        if not nom_utilisateur or not pin or not role:
            print("Nom d'utilisateur, PIN et rôle sont requis.")
            return False
        if role not in ['admin', 'utilisateur']:
            print("Rôle invalide. Doit être 'admin' ou 'utilisateur'.")
            return False
        
        pin_hash = self._hash_pin(pin)
        try:
            self.cursor.execute("""
            INSERT INTO utilisateurs (nom_utilisateur, pin_hash, role)
            VALUES (?, ?, ?)
            """, (nom_utilisateur.lower(), pin_hash, role))
            self.conn.commit()
            print(f"Utilisateur {nom_utilisateur} ajouté avec succès.")
            return True
        except sqlite3.IntegrityError:
            print(f"Erreur: Le nom d'utilisateur '{nom_utilisateur}' existe déjà.")
            return False
        except Exception as e:
            print(f"Erreur lors de l'ajout de l'utilisateur: {e}")
            return False

    def get_user_by_username(self, nom_utilisateur):
        """Récupère un utilisateur par son nom d'utilisateur."""
        try:
            self.cursor.execute("SELECT id, nom_utilisateur, pin_hash, role FROM utilisateurs WHERE nom_utilisateur = ?", (nom_utilisateur.lower(),))
            user_data = self.cursor.fetchone()
            if user_data:
                return {'id': user_data[0], 'nom_utilisateur': user_data[1], 'pin_hash': user_data[2], 'role': user_data[3]}
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération de l'utilisateur: {e}")
            return None

    def verify_pin(self, nom_utilisateur, pin):
        """Vérifie le PIN d'un utilisateur."""
        user = self.get_user_by_username(nom_utilisateur)
        if user and user['pin_hash'] == self._hash_pin(pin):
            print(f"PIN vérifié pour l'utilisateur {nom_utilisateur}.")
            return user # Retourne les données de l'utilisateur en cas de succès
        print(f"Échec de la vérification du PIN pour {nom_utilisateur}.")
        return None

    def migrate_old_database(self):
        """Migre l'ancienne structure de base de données vers la nouvelle si nécessaire."""
        print("Vérification de la structure de la base de données pour migration...")
        try:
            # Vérifier la table articles
            self.cursor.execute("PRAGMA table_info(articles)")
            article_columns = [column[1] for column in self.cursor.fetchall()]
            
            if "position" not in article_columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN position TEXT")
            if "quantite_minimale" not in article_columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN quantite_minimale INTEGER DEFAULT 0")
            if "date_creation" not in article_columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if "date_modification" not in article_columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if "derniere_notification_envoyee" not in article_columns:
                self.cursor.execute("ALTER TABLE articles ADD COLUMN derniere_notification_envoyee TIMESTAMP NULL")

            # Vérifier la table mouvements
            self.cursor.execute("PRAGMA table_info(mouvements)")
            mouvement_columns = [column[1] for column in self.cursor.fetchall()]
            
            if not mouvement_columns: # Si la table mouvement n'existe pas (cas très ancien)
                self.create_tables() # Recrée toutes les tables avec la nouvelle structure
            else:
                if "id_utilisateur" not in mouvement_columns:
                    self.cursor.execute("ALTER TABLE mouvements ADD COLUMN id_utilisateur INTEGER NULL REFERENCES utilisateurs(id) ON DELETE SET NULL")
                if "quantite_avant_mouvement" not in mouvement_columns:
                    self.cursor.execute("ALTER TABLE mouvements ADD COLUMN quantite_avant_mouvement INTEGER DEFAULT 0 NOT NULL") # Mettre une valeur par défaut pour les anciennes données
                if "quantite_apres_mouvement" not in mouvement_columns:
                    self.cursor.execute("ALTER TABLE mouvements ADD COLUMN quantite_apres_mouvement INTEGER DEFAULT 0 NOT NULL") # Mettre une valeur par défaut
                if "quantite_change" not in mouvement_columns:
                    self.cursor.execute("ALTER TABLE mouvements ADD COLUMN quantite_change INTEGER DEFAULT 0 NOT NULL") # Mettre une valeur par défaut
                
                # Renommer commentaire en projet si nécessaire
                if "projet" not in mouvement_columns and "commentaire" in mouvement_columns:
                    # Il est plus sûr de créer une nouvelle table, copier les données, supprimer l'ancienne et renommer
                    # Cependant, pour simplifier, on peut essayer de renommer si la version de SQLite le permet bien
                    # Mais ALTER TABLE RENAME COLUMN n'est supporté qu'à partir de SQLite 3.25.0
                    # Une approche plus robuste est nécessaire si on doit supporter des versions plus anciennes.
                    # Pour l'instant, on suppose une version de SQLite qui le supporte ou on accepte que ce ne soit pas migré.
                    # Alternative: ajouter projet, copier commentaire vers projet, puis supprimer commentaire (plus complexe)
                    print("Tentative de migration de la colonne 'commentaire' vers 'projet' non implémentée pour éviter la complexité.")

                if "travailleur" not in mouvement_columns:
                    self.cursor.execute("ALTER TABLE mouvements ADD COLUMN travailleur TEXT")
                if "type_mouvement" not in mouvement_columns:
                     self.cursor.execute("ALTER TABLE mouvements ADD COLUMN type_mouvement TEXT DEFAULT 'INCONNU' NOT NULL")

            self.conn.commit()
            print("Migration de la base de données terminée.")
            return True
        
        except Exception as e:
            print(f"Erreur lors de la migration de la base de données: {e}")
            # Il est important de ne pas commiter si une erreur survient pendant la migration
            self.conn.rollback()
            return False
    
    def add_article(self, reference, description, quantite=0, quantite_minimale=0, position="", id_utilisateur=None):
        """Ajoute un nouvel article à la base de données et enregistre le mouvement."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
            INSERT INTO articles (reference, description, quantite, quantite_minimale, position, date_creation, date_modification)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (reference, description, quantite, quantite_minimale, position, current_date, current_date))
            
            # Enregistrer le mouvement de création
            self.cursor.execute("""
            INSERT INTO mouvements (article_reference, id_utilisateur, type_mouvement, quantite_avant_mouvement, quantite_apres_mouvement, quantite_change, projet, travailleur)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (reference, id_utilisateur, 'CREATION_ARTICLE', 0, quantite, quantite, 'CREATION', None))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de l'ajout de l'article: {e}")
            self.conn.rollback()
            return False
    
    def update_article(self, reference, description, quantite_minimale=None, position=None, id_utilisateur=None):
        """Met à jour les informations d'un article existant et enregistre le mouvement."""
        try:
            article_avant = self.get_article(reference)
            if not article_avant:
                return False

            current_min_qty, current_position = article_avant[3], article_avant[4]
            
            quantite_minimale = quantite_minimale if quantite_minimale is not None else current_min_qty
            position = position if position is not None else current_position
            
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
            UPDATE articles
            SET description = ?, quantite_minimale = ?, position = ?, date_modification = ?
            WHERE reference = ?
            """, (description, quantite_minimale, position, current_date, reference))
            
            # Enregistrer le mouvement de modification
            # Pour une modification de description/position/min_qty, quantite_avant et quantite_apres sont identiques
            self.cursor.execute("""
            INSERT INTO mouvements (article_reference, id_utilisateur, type_mouvement, 
                                 quantite_avant_mouvement, quantite_apres_mouvement, quantite_change, 
                                 projet, travailleur)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (reference, id_utilisateur, 'MODIFICATION_ARTICLE', article_avant[2], article_avant[2], 0, 'MODIFICATION', None))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de la mise à jour de l'article: {e}")
            self.conn.rollback()
            return False

    def update_quantity(self, reference, quantite_change, type_mouvement, projet=None, travailleur=None, id_utilisateur=None):
        """Met à jour la quantité d'un article et enregistre le mouvement."""
        try:
            if quantite_change == 0:
                print("La quantité à changer ne peut pas être zéro.")
                return False # Ou True, car aucune action n'est nécessaire

            self.cursor.execute("SELECT quantite FROM articles WHERE reference = ?", (reference,))
            result = self.cursor.fetchone()
            if not result:
                print(f"Article non trouvé: {reference}")
                return False
            
            current_quantity = result[0]
            quantite_avant_mouvement = current_quantity

            if type_mouvement == "AJOUT":
                if quantite_change < 0: # Doit être positif pour un ajout
                    print("La quantité pour AJOUT doit être positive.")
                    return False
                new_quantity = current_quantity + quantite_change
                q_change_val = quantite_change
            elif type_mouvement == "RETRAIT":
                if quantite_change < 0: # Doit être positif pour un retrait (on soustrait cette valeur)
                    print("La quantité pour RETRAIT doit être positive (elle sera soustraite).")
                    return False
                if current_quantity < quantite_change:
                    print(f"Quantité insuffisante. Stock actuel: {current_quantity}, Demande: {quantite_change}")
                    raise ValueError(f"Quantité insuffisante. Stock actuel: {current_quantity}")
                new_quantity = current_quantity - quantite_change
                q_change_val = -quantite_change # Négatif pour indiquer un retrait
            else:
                print(f"Type de mouvement non reconnu: {type_mouvement}")
                return False
            
            quantite_apres_mouvement = new_quantity

            self.cursor.execute("""
            UPDATE articles
            SET quantite = ?, date_modification = datetime('now', 'localtime')
            WHERE reference = ?
            """, (new_quantity, reference))
            
            self.cursor.execute("""
            INSERT INTO mouvements (article_reference, id_utilisateur, type_mouvement, 
                                 quantite_avant_mouvement, quantite_apres_mouvement, quantite_change, 
                                 projet, travailleur)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (reference, id_utilisateur, type_mouvement, quantite_avant_mouvement, quantite_apres_mouvement, q_change_val, projet, travailleur))
            
            self.conn.commit()
            return True
        except ValueError as e:
            self.conn.rollback()
            raise e 
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la quantité: {e}")
            self.conn.rollback()
            return False
    
    def delete_article(self, reference, id_utilisateur=None):
        """Supprime un article et ses mouvements associés, enregistre la suppression."""
        try:
            article_avant_suppression = self.get_article(reference)
            if not article_avant_suppression:
                print(f"Article {reference} non trouvé pour suppression.")
                return False

            # Enregistrer le mouvement de suppression AVANT de supprimer l'article
            # car la clé étrangère article_reference dans mouvements pourrait être affectée (ON DELETE CASCADE)
            self.cursor.execute("""
            INSERT INTO mouvements (article_reference, id_utilisateur, type_mouvement, 
                                 quantite_avant_mouvement, quantite_apres_mouvement, quantite_change, 
                                 projet, travailleur)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (reference, id_utilisateur, 'SUPPRESSION_ARTICLE', 
                  article_avant_suppression[2], 0, -article_avant_suppression[2], 
                  'SUPPRESSION', None))
            
            # Supprimer les mouvements n'est plus nécessaire si ON DELETE CASCADE est bien configuré et fonctionne
            # self.cursor.execute("DELETE FROM mouvements WHERE article_reference = ?", (reference,))
            
            self.cursor.execute("DELETE FROM articles WHERE reference = ?", (reference,))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de la suppression de l'article {reference}: {e}")
            self.conn.rollback()
            return False
    
    def get_article(self, reference):
        """Récupère les informations d'un article."""
        try:
            self.cursor.execute("""
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification, derniere_notification_envoyee
            FROM articles
            WHERE reference = ?
            """, (reference,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Erreur lors de la récupération de l'article: {e}")
            return None
    
    def get_all_articles(self):
        """Récupère tous les articles."""
        try:
            self.cursor.execute("""
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification, derniere_notification_envoyee
            FROM articles
            ORDER BY reference
            """)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des articles: {e}")
            return []
    
    def search_articles(self, search_term):
        """Recherche des articles par référence ou description."""
        try:
            search_term_like = f"%{search_term}%"
            self.cursor.execute("""
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification, derniere_notification_envoyee
            FROM articles
            WHERE reference LIKE ? OR description LIKE ?
            ORDER BY reference
            """, (search_term_like, search_term_like))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la recherche d'articles: {e}")
            return []
    
    def get_article_movements(self, reference):
        """Récupère les mouvements d'un article."""
        try:
            self.cursor.execute("""
            SELECT m.id, m.article_reference, m.date_mouvement, m.type_mouvement, 
                   m.quantite_avant_mouvement, m.quantite_apres_mouvement, m.quantite_change, 
                   m.projet, m.travailleur, u.nom_utilisateur
            FROM mouvements m
            LEFT JOIN utilisateurs u ON m.id_utilisateur = u.id
            WHERE m.article_reference = ?
            ORDER BY m.date_mouvement DESC
            """, (reference,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des mouvements: {e}")
            return []

    def get_all_movements_for_stats(self, start_date=None, end_date=None, user_id=None, article_ref=None):
        """Récupère tous les mouvements pour les statistiques, avec filtres optionnels."""
        try:
            query = """
            SELECT m.id, m.article_reference, a.description as article_description, 
                   m.date_mouvement, m.type_mouvement, 
                   m.quantite_avant_mouvement, m.quantite_apres_mouvement, m.quantite_change, 
                   m.projet, m.travailleur, u.nom_utilisateur
            FROM mouvements m
            JOIN articles a ON m.article_reference = a.reference
            LEFT JOIN utilisateurs u ON m.id_utilisateur = u.id
            WHERE 1=1
            """
            params = []
            if start_date:
                query += " AND date(m.date_mouvement) >= date(?)"
                params.append(start_date)
            if end_date:
                query += " AND date(m.date_mouvement) <= date(?)"
                params.append(end_date)
            if user_id:
                query += " AND m.id_utilisateur = ?"
                params.append(user_id)
            if article_ref:
                query += " AND m.article_reference = ?"
                params.append(article_ref)
            
            query += " ORDER BY m.date_mouvement DESC"
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des mouvements pour statistiques: {e}")
            return []

    def get_low_stock_articles(self, threshold=None):
        """Récupère les articles dont la quantité est inférieure à la quantité minimale ou à un seuil."""
        try:
            query = """
            SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification, derniere_notification_envoyee
            FROM articles
            WHERE quantite < 
            """
            if threshold is not None:
                query += "?"
                params = (threshold,)
            else:
                query += "quantite_minimale"
                params = ()
            query += " ORDER BY reference"
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erreur lors de la récupération des articles à stock bas: {e}")
            return []

    def update_last_notification_date(self, reference):
        """Met à jour la date de dernière notification pour un article."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""UPDATE articles SET derniere_notification_envoyee = ? WHERE reference = ?""", (current_date, reference))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la date de notification: {e}")
            self.conn.rollback()
            return False

    def close(self):
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()
            print("Connexion à la base de données fermée")

# Exemple d'utilisation (pourrait être dans un autre fichier ou un test)
if __name__ == '__main__':
    db_manager = DatabaseManager(db_file="data/test_stock_database.db")
    db_manager.connect()
    db_manager.create_tables()
    db_manager.migrate_old_database() # Pour s'assurer que les nouvelles colonnes sont là

    # Ajouter un utilisateur admin
    db_manager.add_user("admin", "admin123", "admin")
    db_manager.add_user("user1", "user123", "utilisateur")

    # Vérifier un utilisateur
    admin_user = db_manager.verify_pin("admin", "admin123")
    if admin_user:
        print(f"Admin connecté: {admin_user}")
        # Ajouter un article
        db_manager.add_article("TEST001", "Article de test", 10, 2, "A1", id_utilisateur=admin_user['id'])
        db_manager.update_quantity("TEST001", 5, "AJOUT", "PROJET_TEST", "TRAV_TEST", id_utilisateur=admin_user['id'])
        db_manager.update_quantity("TEST001", 3, "RETRAIT", "PROJET_TEST", "TRAV_TEST", id_utilisateur=admin_user['id'])
    
    user1_user = db_manager.verify_pin("user1", "user123")
    if user1_user:
        print(f"Utilisateur connecté: {user1_user}")
        db_manager.add_article("TEST002", "Autre article", 5, 1, "B2", id_utilisateur=user1_user['id'])
        try:
            db_manager.update_quantity("TEST002", 10, "RETRAIT", "PROJET_X", "USER_X", id_utilisateur=user1_user['id']) # Devrait échouer
        except ValueError as e:
            print(f"Erreur attendue: {e}")

    print("\nTous les articles:")
    for article in db_manager.get_all_articles():
        print(article)
    
    print("\nMouvements pour TEST001:")
    for movement in db_manager.get_article_movements("TEST001"):
        print(movement)

    print("\nArticles à stock bas:")
    for article in db_manager.get_low_stock_articles():
        print(article)

    db_manager.delete_article("TEST001", id_utilisateur=admin_user['id'] if admin_user else None)
    print("\nArticle TEST001 supprimé.")

    print("\nTous les mouvements pour statistiques:")
    for movement in db_manager.get_all_movements_for_stats():
        print(movement)

    db_manager.close()
    # Supprimer la base de données de test
    if os.path.exists("data/test_stock_database.db"):
        os.remove("data/test_stock_database.db")

