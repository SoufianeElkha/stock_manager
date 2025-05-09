"""
Module pour la gestion et l'affichage des statistiques de stock.
"""

import pandas as pd
from database_design import DatabaseManager
from datetime import datetime, timedelta

class StatsManager:
    """Gère la récupération et la préparation des données pour les statistiques."""
    def __init__(self, db_manager):
        """Initialise le gestionnaire de statistiques.

        Args:
            db_manager (DatabaseManager): Une instance du gestionnaire de base de données.
        """
        self.db_manager = db_manager

    def get_movements_dataframe(self, start_date=None, end_date=None, user_id=None, article_ref=None):
        """Récupère les mouvements et les retourne sous forme de DataFrame pandas.

        Args:
            start_date (str, optional): Date de début (YYYY-MM-DD). Defaults to None.
            end_date (str, optional): Date de fin (YYYY-MM-DD). Defaults to None.
            user_id (int, optional): ID de l'utilisateur. Defaults to None.
            article_ref (str, optional): Référence de l'article. Defaults to None.

        Returns:
            pandas.DataFrame: DataFrame contenant les mouvements, ou None en cas d'erreur.
        """
        try:
            movements_data = self.db_manager.get_all_movements_for_stats(
                start_date=start_date, 
                end_date=end_date, 
                user_id=user_id, 
                article_ref=article_ref
            )
            if not movements_data:
                return pd.DataFrame() # Retourne un DataFrame vide si pas de données

            columns = [
                'id_mouvement', 'reference_article', 'description_article', 'date_mouvement', 
                'type_mouvement', 'qte_avant', 'qte_apres', 'qte_changee', 
                'projet', 'travailleur', 'nom_utilisateur'
            ]
            df = pd.DataFrame(movements_data, columns=columns)
            df['date_mouvement'] = pd.to_datetime(df['date_mouvement'])
            return df
        except Exception as e:
            print(f"Erreur lors de la création du DataFrame des mouvements: {e}")
            return None

    def get_summary_stats(self, df_movements):
        """Calcule des statistiques sommaires à partir du DataFrame des mouvements.

        Args:
            df_movements (pandas.DataFrame): DataFrame des mouvements.

        Returns:
            dict: Un dictionnaire contenant des statistiques sommaires.
        """
        if df_movements is None or df_movements.empty:
            return {
                'total_mouvements': 0,
                'total_entrees': 0,
                'total_sorties': 0,
                'articles_plus_mouvementes': [],
                'utilisateurs_plus_actifs': []
            }

        total_mouvements = len(df_movements)
        total_entrees = df_movements[df_movements['type_mouvement'].isin(['AJOUT_STOCK', 'CREATION_ARTICLE', 'IMPORT_EXCEL'])]['qte_changee'].sum()
        total_sorties = abs(df_movements[df_movements['type_mouvement'].isin(['RETRAIT_STOCK'])]['qte_changee'].sum())
        
        # Articles les plus mouvementés (basé sur le nombre de mouvements)
        articles_plus_mouvementes = df_movements['description_article'].value_counts().nlargest(5).reset_index()
        articles_plus_mouvementes.columns = ['article', 'nombre_mouvements']

        # Utilisateurs les plus actifs (si l'information est disponible)
        if 'nom_utilisateur' in df_movements.columns and not df_movements['nom_utilisateur'].isnull().all():
            utilisateurs_plus_actifs = df_movements['nom_utilisateur'].value_counts().nlargest(5).reset_index()
            utilisateurs_plus_actifs.columns = ['utilisateur', 'nombre_actions']
        else:
            utilisateurs_plus_actifs = pd.DataFrame(columns=['utilisateur', 'nombre_actions'])

        return {
            'total_mouvements': total_mouvements,
            'total_quantite_entree': total_entrees,
            'total_quantite_sortie': total_sorties,
            'articles_plus_mouvementes': articles_plus_mouvementes.to_dict(orient='records'),
            'utilisateurs_plus_actifs': utilisateurs_plus_actifs.to_dict(orient='records')
        }

    def get_stock_evolution(self, article_ref, start_date=None, end_date=None):
        """Suit l'évolution du stock pour un article spécifique.

        Args:
            article_ref (str): Référence de l'article.
            start_date (str, optional): Date de début.
            end_date (str, optional): Date de fin.

        Returns:
            pandas.DataFrame: DataFrame avec date et quantité, ou None.
        """
        df_article_movements = self.get_movements_dataframe(article_ref=article_ref, start_date=start_date, end_date=end_date)
        if df_article_movements is None or df_article_movements.empty:
            # Essayer de récupérer la quantité actuelle si pas de mouvements dans la période
            article_data = self.db_manager.get_article(article_ref)
            if article_data:
                return pd.DataFrame([{'date_mouvement': pd.to_datetime(datetime.now()), 'qte_apres': article_data[2]}])
            return pd.DataFrame(columns=['date_mouvement', 'qte_apres'])

        # Trier par date pour s'assurer de l'ordre chronologique
        df_article_movements = df_article_movements.sort_values(by='date_mouvement')
        
        # Garder uniquement la date et la quantité après mouvement
        evolution_df = df_article_movements[['date_mouvement', 'qte_apres']].copy()
        evolution_df.rename(columns={'qte_apres': 'quantite'}, inplace=True)
        
        # Ajouter le point de départ (quantité avant le premier mouvement de la période)
        if not evolution_df.empty:
            first_movement = df_article_movements.iloc[0]
            start_point = pd.DataFrame([{
                'date_mouvement': first_movement['date_mouvement'] - timedelta(seconds=1), 
                'quantite': first_movement['qte_avant']
            }])
            evolution_df = pd.concat([start_point, evolution_df], ignore_index=True)
        else: # Si pas de mouvements, mais l'article existe, prendre sa quantité actuelle
            article_info = self.db_manager.get_article(article_ref)
            if article_info:
                now = pd.to_datetime(datetime.now())
                evolution_df = pd.DataFrame([{'date_mouvement': now, 'quantite': article_info[2]}])

        return evolution_df

    def get_low_stock_report(self):
        """Génère un rapport des articles à stock bas.

        Returns:
            pandas.DataFrame: DataFrame des articles à stock bas.
        """
        low_stock_data = self.db_manager.get_low_stock_articles()
        if not low_stock_data:
            return pd.DataFrame()
        
        columns = ['reference', 'description', 'quantite', 'quantite_minimale', 'position', 
                   'date_creation', 'date_modification', 'derniere_notification_envoyee']
        df = pd.DataFrame(low_stock_data, columns=columns)
        df['deficit'] = df['quantite_minimale'] - df['quantite']
        return df[['reference', 'description', 'quantite', 'quantite_minimale', 'deficit', 'position']]

# Exemple d'utilisation
if __name__ == '__main__':
    # Configuration initiale pour le test
    db_path_test = "data/stats_test_db.sqlite"
    if os.path.exists(db_path_test):
        os.remove(db_path_test)

    db_man = DatabaseManager(db_file=db_path_test)
    db_man.connect()
    db_man.create_tables()
    db_man.migrate_old_database()

    # Ajouter des utilisateurs et des données
    if not db_man.get_user_by_username("stats_admin"):
        db_man.add_user("stats_admin", "adminpass", "admin")
    admin_user = db_man.get_user_by_username("stats_admin")
    uid = admin_user['id'] if admin_user else None

    db_man.add_article("STAT001", "Article pour Stats 1", 50, 10, "S1", id_utilisateur=uid)
    db_man.add_article("STAT002", "Article pour Stats 2", 30, 5, "S2", id_utilisateur=uid)

    db_man.update_quantity("STAT001", 10, "AJOUT", "Projet Alpha", "Admin", id_utilisateur=uid)
    db_man.update_quantity("STAT001", 5, "RETRAIT", "Projet Beta", "Admin", id_utilisateur=uid)
    db_man.update_quantity("STAT002", 20, "AJOUT", "Projet Alpha", "Admin", id_utilisateur=uid)
    db_man.update_quantity("STAT001", 40, "RETRAIT", "Projet Gamma", "Admin", id_utilisateur=uid) # Stock bas

    stats_mgr = StatsManager(db_man)

    print("--- DataFrame des Mouvements ---")
    df_mouvements = stats_mgr.get_movements_dataframe()
    if df_mouvements is not None:
        print(df_mouvements.head())
    
    print("\n--- Statistiques Sommaires ---")
    summary = stats_mgr.get_summary_stats(df_mouvements)
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n--- Évolution du Stock pour STAT001 ---")
    df_evolution_stat001 = stats_mgr.get_stock_evolution("STAT001")
    if df_evolution_stat001 is not None:
        print(df_evolution_stat001)

    print("\n--- Rapport des Stocks Bas ---")
    df_low_stock = stats_mgr.get_low_stock_report()
    if df_low_stock is not None:
        print(df_low_stock)

    # Nettoyage
    db_man.close()
    if os.path.exists(db_path_test):
        os.remove(db_path_test)

