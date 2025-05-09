"""
Module pour la gestion des notifications de stock bas.
"""

from datetime import datetime, timedelta
# Assurez-vous que database_design.py est accessible ou ajustez l'import
# from database_design import DatabaseManager 

class NotificationManager:
    """Gère la détection des stocks bas et la logique de notification."""

    def __init__(self, db_manager):
        """Initialise le gestionnaire de notifications.

        Args:
            db_manager (DatabaseManager): Une instance du gestionnaire de base de données.
        """
        self.db_manager = db_manager
        # Intervalle minimum entre les notifications pour le même article (par exemple, 1 jour)
        self.notification_interval = timedelta(days=1)

    def check_low_stock_articles(self):
        """Vérifie les articles en stock bas qui nécessitent une notification.

        Returns:
            list: Une liste de dictionnaires, chaque dictionnaire représentant un article 
                  nécessitant une notification. Retourne une liste vide si aucun.
        """
        articles_to_notify = []
        try:
            # Récupérer tous les articles où la quantité actuelle est inférieure à la quantité minimale
            low_stock_articles_data = self.db_manager.get_low_stock_articles()
            
            if not low_stock_articles_data:
                return []

            now = datetime.now()

            for article_data in low_stock_articles_data:
                # Les colonnes attendues de get_low_stock_articles sont:
                # reference, description, quantite, quantite_minimale, position, 
                # date_creation, date_modification, derniere_notification_envoyee
                reference = article_data[0]
                description = article_data[1]
                quantite_actuelle = article_data[2]
                quantite_minimale = article_data[3]
                derniere_notification_str = article_data[7]

                derniere_notification_dt = None
                if derniere_notification_str:
                    try:
                        # S'assurer que le format correspond à celui stocké dans la DB
                        derniere_notification_dt = datetime.strptime(derniere_notification_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError as ve:
                        print(f"Avertissement: Format de date incorrect pour derniere_notification_envoyee pour l'article {reference}: {ve}. Traitement comme si aucune notification n'a été envoyée.")
                
                if derniere_notification_dt is None or (now - derniere_notification_dt > self.notification_interval):
                    articles_to_notify.append({
                        "reference": reference,
                        "description": description,
                        "quantite_actuelle": quantite_actuelle,
                        "quantite_minimale": quantite_minimale
                    })
            return articles_to_notify
        except Exception as e:
            print(f"Erreur lors de la vérification des articles en stock bas: {e}")
            return [] # Retourne une liste vide en cas d'erreur

    def record_notification_sent(self, article_reference):
        """Enregistre qu'une notification a été envoyée pour un article.

        Args:
            article_reference (str): La référence de l'article.

        Returns:
            bool: True si l'enregistrement a réussi, False sinon.
        """
        try:
            success = self.db_manager.update_last_notification_date(article_reference)
            if success:
                print(f"Date de dernière notification mise à jour pour l'article {article_reference}.")
            else:
                print(f"Échec de la mise à jour de la date de dernière notification pour {article_reference}.")
            return success
        except Exception as e:
            print(f"Erreur lors de l'enregistrement de la notification envoyée pour {article_reference}: {e}")
            return False

# Exemple d'utilisation (nécessite une instance de DatabaseManager configurée)
if __name__ == '__main__':
    import os
    # Ceci est un exemple simplifié. Dans une application réelle, db_manager serait déjà initialisé.
    # Assurez-vous que le chemin vers database_design est correct si vous exécutez ce fichier directement.
    # Pour cet exemple, nous allons supposer que database_design.py est dans le même répertoire ou accessible via PYTHONPATH.
    try:
        from database_design import DatabaseManager
    except ImportError:
        print("Erreur: Impossible d'importer DatabaseManager. Assurez-vous que database_design.py est accessible.")
        exit()

    # Configuration initiale pour le test
    db_path_test = "data/notification_test_db.sqlite"
    if os.path.exists(db_path_test):
        os.remove(db_path_test)
    
    db_man = DatabaseManager(db_file=db_path_test)
    db_man.connect()
    db_man.create_tables()
    db_man.migrate_old_database() # S'assurer que les nouvelles colonnes sont là

    # Ajouter un utilisateur admin pour les opérations
    if not db_man.get_user_by_username("notif_admin"):
        db_man.add_user("notif_admin", "notifpass", "admin")
    admin_user = db_man.get_user_by_username("notif_admin")
    uid = admin_user['id'] if admin_user else None

    # Ajouter des articles de test
    db_man.add_article("NOTIF001", "Article Test Notification 1", 5, 10, "N1", id_utilisateur=uid) # Stock bas
    db_man.add_article("NOTIF002", "Article Test Notification 2", 15, 10, "N2", id_utilisateur=uid) # Stock OK
    db_man.add_article("NOTIF003", "Article Test Notification 3", 2, 5, "N3", id_utilisateur=uid) # Stock bas

    notif_mgr = NotificationManager(db_man)

    print("\n--- Vérification des articles en stock bas pour notification ---")
    articles_a_notifier = notif_mgr.check_low_stock_articles()
    if articles_a_notifier:
        print(f"{len(articles_a_notifier)} article(s) nécessitent une notification:")
        for article in articles_a_notifier:
            print(f"  - {article['description']} (Réf: {article['reference']}), Actuel: {article['quantite_actuelle']}, Min: {article['quantite_minimale']}")
            # Simuler l'envoi et enregistrer
            notif_mgr.record_notification_sent(article['reference'])
    else:
        print("Aucun article ne nécessite de notification pour le moment.")

    print("\n--- Nouvelle vérification après enregistrement des notifications ---")
    articles_a_notifier_apres = notif_mgr.check_low_stock_articles()
    if not articles_a_notifier_apres:
        print("Aucun article ne nécessite de notification (attendu après enregistrement).")
    else:
        print(f"{len(articles_a_notifier_apres)} article(s) nécessitent encore une notification (inattendu).")
        for article in articles_a_notifier_apres:
            print(f"  - {article['description']}")
            
    # Simuler le passage du temps (plus que l'intervalle de notification)
    # Pour un test réel, il faudrait manipuler les dates dans la DB ou attendre.
    # Ici, nous allons modifier manuellement la date de dernière notification pour un article pour retester.
    print("\n--- Simulation du passage du temps et nouvelle vérification pour NOTIF001 ---")
    # Mettre une date de notification ancienne pour NOTIF001
    ancienne_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    db_man.cursor.execute("UPDATE articles SET derniere_notification_envoyee = ? WHERE reference = ?", (ancienne_date, "NOTIF001"))
    db_man.conn.commit()
    
    articles_a_notifier_temps_passe = notif_mgr.check_low_stock_articles()
    article_notif001_trouve = False
    if articles_a_notifier_temps_passe:
        print(f"{len(articles_a_notifier_temps_passe)} article(s) nécessitent une notification après simulation du temps:")
        for article in articles_a_notifier_temps_passe:
            print(f"  - {article['description']} (Réf: {article['reference']})")
            if article['reference'] == "NOTIF001":
                article_notif001_trouve = True
    else:
        print("Aucun article ne nécessite de notification après simulation du temps.")
    
    if article_notif001_trouve:
        print("Test réussi: NOTIF001 est de nouveau listé pour notification après l'intervalle.")
    else:
        print("Test échoué ou NOTIF001 n'est plus en stock bas / déjà notifié récemment.")

    # Nettoyage
    db_man.close()
    if os.path.exists(db_path_test):
        os.remove(db_path_test)
    print("\nBase de données de test des notifications supprimée.")


