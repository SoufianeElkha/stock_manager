"""
Module de gestion de l'authentification pour le Gestionnaire de Stock.
"""

import hashlib
from database_design import DatabaseManager

class AuthManager:
    """Gère l'authentification des utilisateurs et la session."""
    def __init__(self, db_manager):
        """Initialise le gestionnaire d'authentification.

        Args:
            db_manager (DatabaseManager): Une instance du gestionnaire de base de données.
        """
        self.db_manager = db_manager
        self.current_user = None  # Stocke les informations de l'utilisateur connecté

    def _hash_pin(self, pin):
        """Hashe un PIN en utilisant SHA256. (Méthode privée, dupliquée pour autonomie si besoin)"""
        return hashlib.sha256(pin.encode()).hexdigest()

    def login(self, username, pin):
        """Tente de connecter un utilisateur avec son nom d'utilisateur et son PIN.

        Args:
            username (str): Le nom d'utilisateur.
            pin (str): Le PIN en clair.

        Returns:
            bool: True si la connexion est réussie, False sinon.
        """
        user_data = self.db_manager.verify_pin(username, pin)
        if user_data:
            self.current_user = {
                'id': user_data['id'],
                'username': user_data['nom_utilisateur'],
                'role': user_data['role']
            }
            print(f"Utilisateur {self.current_user['username']} (rôle: {self.current_user['role']}) connecté.")
            return True
        self.current_user = None
        return False

    def logout(self):
        """Déconnecte l'utilisateur actuel."""
        if self.current_user:
            print(f"Utilisateur {self.current_user['username']} déconnecté.")
        self.current_user = None

    def get_current_user(self):
        """Retourne les informations de l'utilisateur actuellement connecté."""
        return self.current_user

    def is_admin(self):
        """Vérifie si l'utilisateur actuel est un administrateur."""
        return self.current_user and self.current_user['role'] == 'admin'

    def add_user(self, username, pin, role='utilisateur'):
        """Ajoute un nouvel utilisateur. (Raccourci vers db_manager.add_user)
           Normalement, cette action devrait être réservée aux administrateurs.
        """
        if self.is_admin(): # S'assurer que seul un admin peut ajouter des utilisateurs
            return self.db_manager.add_user(username, pin, role)
        else:
            print("Action non autorisée: Seul un administrateur peut ajouter des utilisateurs.")
            return False

# Exemple d'utilisation (pourrait être dans run_app.py ou des tests)
if __name__ == '__main__':
    # Configuration initiale pour le test
    db_path_test = "data/auth_test_db.sqlite"
    if os.path.exists(db_path_test):
        os.remove(db_path_test)
    
    db_man = DatabaseManager(db_file=db_path_test)
    db_man.connect()
    db_man.create_tables() # S'assure que la table utilisateurs est créée
    
    # Créer un utilisateur admin initial s'il n'existe pas
    if not db_man.get_user_by_username("admin"):
        db_man.add_user("admin", "admin123", "admin")
    if not db_man.get_user_by_username("testuser"):
        db_man.add_user("testuser", "test123", "utilisateur")

    auth = AuthManager(db_man)

    # Test de connexion
    print("\n--- Test de Connexion ---")
    if auth.login("admin", "admin123"):
        print(f"Connexion réussie: {auth.get_current_user()}")
        print(f"Est admin: {auth.is_admin()}")
        # Test d'ajout d'utilisateur par un admin
        auth.add_user("newuser", "newpin123", "utilisateur")
        auth.logout()
    else:
        print("Connexion admin échouée.")

    if auth.login("testuser", "test123"):
        print(f"Connexion réussie: {auth.get_current_user()}")
        print(f"Est admin: {auth.is_admin()}")
        # Test d'ajout d'utilisateur par un non-admin
        auth.add_user("anotheruser", "pin456", "utilisateur") 
        auth.logout()
    else:
        print("Connexion testuser échouée.")

    # Test de connexion échouée
    if not auth.login("admin", "wrongpin"):
        print("Test de PIN incorrect réussi.")
    
    # Nettoyage
    db_man.close()
    if os.path.exists(db_path_test):
        os.remove(db_path_test)

