"""
Module principal pour la logique métier du gestionnaire de stock.
Ce module fait le lien entre l'interface utilisateur et la base de données,
intégrant la gestion des utilisateurs pour la traçabilité.
"""

import os
import sys
import pandas as pd
from database_design import DatabaseManager
# from auth_manager import AuthManager # Non importé directement ici, passé en argument

class StockManager:
    """Gestionnaire de stock avec fonctionnalités d'ajout, de retrait d'articles, et traçabilité utilisateur."""
    
    def __init__(self, db_manager: DatabaseManager, auth_manager):
        """Initialise le gestionnaire de stock.

        Args:
            db_manager (DatabaseManager): Instance du gestionnaire de base de données.
            auth_manager (AuthManager): Instance du gestionnaire d'authentification.
        """
        self.db_manager = db_manager
        self.auth_manager = auth_manager
        # La connexion et la création/migration des tables sont gérées à un niveau supérieur (ex: App init)

    def _get_current_user_id(self):
        """Récupère l'ID de l'utilisateur actuellement connecté."""
        current_user = self.auth_manager.get_current_user()
        return current_user["id"] if current_user else None

    def get_all_articles(self):
        """Récupère tous les articles du stock."""
        try:
            rows = self.db_manager.get_all_articles()
            articles = []
            for row in rows:
                articles.append({
                    'reference': row[0],
                    'description': row[1],
                    'quantite': row[2],
                    'quantite_minimale': row[3],
                    'position': row[4],
                    'date_creation': row[5],
                    'date_modification': row[6],
                    'derniere_notification_envoyee': row[7]
                })
            return articles
        except Exception as e:
            print(f"Erreur StockManager - get_all_articles: {e}")
            return []

    def search_articles(self, search_term):
        """Recherche des articles par référence ou description."""
        try:
            rows = self.db_manager.search_articles(search_term)
            articles = []
            for row in rows:
                articles.append({
                    'reference': row[0],
                    'description': row[1],
                    'quantite': row[2],
                    'quantite_minimale': row[3],
                    'position': row[4],
                    'date_creation': row[5],
                    'date_modification': row[6],
                    'derniere_notification_envoyee': row[7]
                })
            return articles
        except Exception as e:
            print(f"Erreur StockManager - search_articles: {e}")
            return []

    def get_article_movements(self, reference):
        """Récupère l'historique des mouvements d'un article."""
        try:
            rows = self.db_manager.get_article_movements(reference)
            movements = []
            for row in rows:
                # Colonnes de get_article_movements dans db_manager:
                # m.id, m.article_reference, m.date_mouvement, m.type_mouvement, 
                # m.quantite_avant_mouvement, m.quantite_apres_mouvement, m.quantite_change, 
                # m.projet, m.travailleur, u.nom_utilisateur
                movements.append({
                    'id_mouvement': row[0],
                    'reference_article': row[1],
                    'date_mouvement': row[2],
                    'type_mouvement': row[3],
                    'quantite_avant_mouvement': row[4],
                    'quantite_apres_mouvement': row[5],
                    'quantite_change': row[6],
                    'projet': row[7],
                    'travailleur': row[8], # Ce champ est conservé pour la saisie manuelle
                    'nom_utilisateur': row[9] # Utilisateur système qui a fait l'action
                })
            return movements
        except Exception as e:
            print(f"Erreur StockManager - get_article_movements: {e}")
            return []

    def add_article(self, reference, description, quantite=0, position="", quantite_minimale=0):
        """Ajoute un nouvel article au stock."""
        reference = reference.upper()
        position = position.upper() if position else ""
        user_id = self._get_current_user_id()

        article_existant = self.db_manager.get_article(reference)
        if article_existant:
            return (False, "EXISTS")

        success = self.db_manager.add_article(reference, description, quantite, quantite_minimale, position, id_utilisateur=user_id)
        if success:
            return (True, "Article ajouté avec succès")
        else:
            return (False, "Erreur lors de l'ajout de l'article")

    def update_article_description_position_min_qty(self, reference, new_description, new_quantite_minimale, new_position):
        """Met à jour la description, la position et la quantité minimale d'un article existant."""
        reference = reference.upper()
        new_position = new_position.upper() if new_position else ""
        user_id = self._get_current_user_id()
        
        # La méthode update_article de db_manager gère la logique de mise à jour et l'enregistrement du mouvement.
        success = self.db_manager.update_article(reference, new_description, new_quantite_minimale, new_position, id_utilisateur=user_id)
        return success

    def add_stock(self, reference, quantite_ajout, projet=None, travailleur=None):
        """Ajoute du stock à un article existant."""
        if not isinstance(quantite_ajout, int) or quantite_ajout <= 0:
            print("La quantité à ajouter doit être un entier positif.")
            return False
        
        reference = reference.upper()
        projet = projet.upper() if projet else None
        travailleur = travailleur.upper() if travailleur else self.auth_manager.get_current_user()["username"] # Par défaut l'utilisateur connecté
        user_id = self._get_current_user_id()

        return self.db_manager.update_quantity(reference, quantite_ajout, "AJOUT", projet, travailleur, id_utilisateur=user_id)

    def remove_stock(self, reference, quantite_retrait, projet=None, travailleur=None):
        """Retire du stock d'un article existant."""
        if not isinstance(quantite_retrait, int) or quantite_retrait <= 0:
            print("La quantité à retirer doit être un entier positif.")
            return False

        reference = reference.upper()
        projet = projet.upper() if projet else None
        travailleur = travailleur.upper() if travailleur else self.auth_manager.get_current_user()["username"]
        user_id = self._get_current_user_id()
        
        try:
            return self.db_manager.update_quantity(reference, quantite_retrait, "RETRAIT", projet, travailleur, id_utilisateur=user_id)
        except ValueError as e: # Capturer l'erreur de quantité insuffisante
            print(f"Erreur StockManager - remove_stock: {e}")
            messagebox.showerror("Stock Insuffisant", str(e)) # Nécessite d'importer messagebox si utilisé ici
            return False

    def delete_article(self, reference):
        """Supprime un article du stock."""
        reference = reference.upper()
        user_id = self._get_current_user_id()
        return self.db_manager.delete_article(reference, id_utilisateur=user_id)

    def get_article_by_reference(self, reference):
        """Récupère un article par sa référence."""
        try:
            reference = reference.upper()
            row = self.db_manager.get_article(reference)
            if row:
                return {
                    'reference': row[0],
                    'description': row[1],
                    'quantite': row[2],
                    'quantite_minimale': row[3],
                    'position': row[4],
                    'date_creation': row[5],
                    'date_modification': row[6],
                    'derniere_notification_envoyee': row[7]
                }
            return None
        except Exception as e:
            print(f"Erreur StockManager - get_article_by_reference: {e}")
            return None

    def get_low_stock_articles(self):
        """Récupère les articles dont le stock est inférieur à la quantité minimale."""
        try:
            rows = self.db_manager.get_low_stock_articles()
            articles = []
            for row in rows:
                articles.append({
                    'reference': row[0],
                    'description': row[1],
                    'quantite': row[2],
                    'quantite_minimale': row[3],
                    'position': row[4],
                    'date_creation': row[5],
                    'date_modification': row[6],
                    'derniere_notification_envoyee': row[7]
                })
            return articles
        except Exception as e:
            print(f"Erreur StockManager - get_low_stock_articles: {e}")
            return []

    def import_from_excel(self, file_path):
        """Importe des articles depuis un fichier Excel."""
        # La vérification par mot de passe est supprimée, l'accès est géré par l'authentification utilisateur.
        user_id = self._get_current_user_id()
        username = self.auth_manager.get_current_user()["username"] if user_id else "SYSTEM_IMPORT"

        try:
            df = pd.read_excel(file_path)
            required_columns = ['reference', 'description']
            for col in required_columns:
                if col not in df.columns:
                    return (False, f"Colonne '{col}' manquante dans le fichier Excel", None)

            stats = {'added': 0, 'updated': 0, 'errors': 0, 'skipped_no_change': 0}

            for _, row in df.iterrows():
                try:
                    reference = str(row['reference']).strip().upper()
                    description = str(row['description']).strip()
                    
                    quantite_import = int(row.get('quantite', 0) or 0)
                    quantite_minimale = int(row.get('quantite_minimale', 0) or 0)
                    position = str(row.get('position', "")).strip().upper()

                    if not reference or not description:
                        print(f"Ligne ignorée: référence ou description manquante ({row.get('reference')}, {row.get('description')})")
                        stats['errors'] +=1
                        continue

                    article_existant = self.db_manager.get_article(reference)

                    if article_existant:
                        # Article existe: mise à jour de la description, qte_min, position.
                        # La quantité est ajoutée comme un mouvement séparé.
                        self.db_manager.update_article(reference, description, quantite_minimale, position, id_utilisateur=user_id)
                        stats['updated'] += 1
                        
                        # Si une quantité est spécifiée dans l'Excel, l'ajouter comme un mouvement.
                        if quantite_import > 0:
                            self.db_manager.update_quantity(reference, quantite_import, "AJOUT", "IMPORT EXCEL", username, id_utilisateur=user_id)
                            # Pas de comptage séparé pour l'ajout de quantité ici, c'est inclus dans 'updated'
                        elif quantite_import < 0:
                             print(f"Quantité négative ({quantite_import}) pour l'article {reference} dans l'Excel ignorée. Utilisez un mouvement de retrait.")
                    else:
                        # Nouvel article
                        self.db_manager.add_article(reference, description, quantite_import, quantite_minimale, position, id_utilisateur=user_id)
                        stats['added'] += 1
                except Exception as e_row:
                    print(f"Erreur lors du traitement de la ligne pour l'article {row.get('reference', 'INCONNU')}: {e_row}")
                    stats['errors'] += 1
            
            return (True, f"Importation terminée.", stats)
        except Exception as e_file:
            print(f"Erreur majeure lors de l'importation du fichier Excel: {e_file}")
            return (False, f"Erreur lors de l'importation: {e_file}", None)

# Exemple d'utilisation (pourrait être dans des tests ou run_app.py)
if __name__ == '__main__':
    # Nécessite une initialisation de AuthManager et DatabaseManager pour tester
    # from auth_manager import AuthManager # Pourrait être nécessaire pour l'exemple
    print("StockManager - Exemple d'utilisation (nécessite une configuration complète)")
    
    # db_m = DatabaseManager("data/dev_stock.db")
    # db_m.connect()
    # db_m.create_tables()
    # auth_m = AuthManager(db_m)
    # if not db_m.get_user_by_username("dev"): db_m.add_user("dev", "dev", "admin")
    # auth_m.login("dev", "dev")

    # stock_m = StockManager(db_m, auth_m)
    
    # print("Tous les articles:", stock_m.get_all_articles())
    # stock_m.add_article("SMT001", "Test depuis StockManager", 10, "Z1", 2)
    # print("Article SMT001:", stock_m.get_article_by_reference("SMT001"))
    # stock_m.add_stock("SMT001", 5, "PROJET_SM", "DEV_USER")
    # print("Article SMT001 après ajout:", stock_m.get_article_by_reference("SMT001"))
    # print("Mouvements SMT001:", stock_m.get_article_movements("SMT001"))
    
    # db_m.close()

