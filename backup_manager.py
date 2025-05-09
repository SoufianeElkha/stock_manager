"""
Module pour la gestion des sauvegardes de la base de données.
"""

import os
import shutil
import datetime
import glob

class BackupManager:
    """Gère la création, la restauration et la gestion des sauvegardes de la base de données."""

    def __init__(self, db_file_path, backup_dir="data/backups"):
        """Initialise le gestionnaire de sauvegardes.

        Args:
            db_file_path (str): Chemin complet vers le fichier de la base de données à sauvegarder.
            backup_dir (str, optional): Répertoire où stocker les sauvegardes. 
                                      Defaults to "data/backups".
        """
        self.db_file_path = db_file_path
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def _get_backup_filename(self, timestamp=None, suffix="_manual"):
        """Génère un nom de fichier pour la sauvegarde.
        Le format sera: YYYYMMDD_HHMMSS_basename_suffix.db
        """
        if not timestamp:
            timestamp = datetime.datetime.now()
        
        db_basename = os.path.basename(self.db_file_path)
        # Enlever l'extension .db ou .sqlite pour le nom de base
        base, _ = os.path.splitext(db_basename)
        
        return timestamp.strftime("%Y%m%d_%H%M%S") + f"_{base}{suffix}.db"

    def create_backup(self, suffix="_manual"):
        """Crée une sauvegarde du fichier de la base de données.

        Args:
            suffix (str, optional): Un suffixe à ajouter au nom du fichier de sauvegarde 
                                    (par exemple, "_daily", "_weekly"). Defaults to "_manual".

        Returns:
            str: Le chemin du fichier de sauvegarde créé, ou None en cas d'échec.
        """
        if not os.path.exists(self.db_file_path):
            print(f"Erreur: Le fichier de base de données '{self.db_file_path}' n'existe pas.")
            return None

        backup_filename = self._get_backup_filename(suffix=suffix)
        backup_file_path = os.path.join(self.backup_dir, backup_filename)

        try:
            shutil.copy2(self.db_file_path, backup_file_path)
            print(f"Sauvegarde créée avec succès: {backup_file_path}")
            return backup_file_path
        except Exception as e:
            print(f"Erreur lors de la création de la sauvegarde: {e}")
            return None

    def list_backups(self):
        """Liste toutes les sauvegardes disponibles, triées par date (la plus récente en premier)."""
        backup_files = glob.glob(os.path.join(self.backup_dir, "*.db"))
        # Trier par nom de fichier, ce qui devrait correspondre à la date grâce au format du nom
        backup_files.sort(reverse=True)
        return backup_files

    def restore_backup(self, backup_file_name=None):
        """Restaure la base de données à partir d'une sauvegarde spécifiée ou de la plus récente.

        Args:
            backup_file_name (str, optional): Le nom du fichier de sauvegarde à restaurer 
                                              (doit exister dans le répertoire de sauvegarde).
                                              Si None, la sauvegarde la plus récente est utilisée.

        Returns:
            bool: True si la restauration a réussi, False sinon.
        """
        if backup_file_name:
            backup_to_restore_path = os.path.join(self.backup_dir, backup_file_name)
            if not os.path.exists(backup_to_restore_path):
                print(f"Erreur: Le fichier de sauvegarde '{backup_file_name}' n'existe pas dans '{self.backup_dir}'.")
                return False
        else:
            available_backups = self.list_backups()
            if not available_backups:
                print("Aucune sauvegarde disponible pour la restauration.")
                return False
            backup_to_restore_path = available_backups[0] # La plus récente
            backup_file_name = os.path.basename(backup_to_restore_path)

        try:
            # Optionnel: créer une sauvegarde de l'état actuel avant de restaurer
            # self.create_backup(suffix="_pre_restore")
            
            shutil.copy2(backup_to_restore_path, self.db_file_path)
            print(f"Base de données restaurée avec succès à partir de: {backup_file_name}")
            return True
        except Exception as e:
            print(f"Erreur lors de la restauration de la sauvegarde: {e}")
            return False

    def manage_backups(self, max_backups=7):
        """Gère les sauvegardes en supprimant les plus anciennes si le nombre maximal est dépassé.
        Ne supprime que les sauvegardes avec des suffixes courants comme _manual, _daily, _auto.
        Les sauvegardes avec des suffixes spécifiques (ex: _pre_restore, _archive) pourraient être conservées.
        
        Args:
            max_backups (int, optional): Nombre maximal de sauvegardes à conserver. Defaults to 7.
        """
        available_backups = self.list_backups()
        
        # Filtrer pour ne considérer que les sauvegardes "normales" pour la rotation
        # Ceci est une heuristique simple basée sur le nom de fichier
        eligible_for_deletion = [b for b in available_backups if any(s in os.path.basename(b) for s in ["_manual", "_daily", "_auto"])]
        eligible_for_deletion.sort(reverse=True) # Les plus récentes en premier

        if len(eligible_for_deletion) > max_backups:
            num_to_delete = len(eligible_for_deletion) - max_backups
            backups_to_delete = eligible_for_deletion[-num_to_delete:] # Les plus anciennes de la liste éligible
            
            print(f"Gestion des sauvegardes: {len(eligible_for_deletion)} sauvegardes éligibles trouvées, conservation de {max_backups}.")
            for backup_file in backups_to_delete:
                try:
                    os.remove(backup_file)
                    print(f"Ancienne sauvegarde supprimée: {os.path.basename(backup_file)}")
                except Exception as e:
                    print(f"Erreur lors de la suppression de l'ancienne sauvegarde {os.path.basename(backup_file)}: {e}")
        else:
            print(f"Gestion des sauvegardes: {len(eligible_for_deletion)} sauvegardes éligibles, aucune suppression nécessaire (max: {max_backups}).")

# Exemple d'utilisation
if __name__ == '__main__':
    # Créer un fichier de base de données factice pour le test
    dummy_db_path = "data/test_app_db.sqlite"
    os.makedirs("data", exist_ok=True)
    with open(dummy_db_path, "w") as f:
        f.write("Ceci est une base de données de test.")

    backup_mgr = BackupManager(db_file_path=dummy_db_path, backup_dir="data/test_backups")

    print("\n--- Création de sauvegardes ---")
    backup_mgr.create_backup(suffix="_manual_test1")
    backup_mgr.create_backup(suffix="_daily_test")
    # Simuler plusieurs sauvegardes
    for i in range(5):
        with open(dummy_db_path, "a") as f:
            f.write(f"\nModification {i+1}")
        backup_mgr.create_backup(suffix=f"_auto_test_{i}")
        # time.sleep(1) # Pour s'assurer que les timestamps sont différents si nécessaire

    print("\n--- Liste des sauvegardes ---")
    backups = backup_mgr.list_backups()
    for b in backups:
        print(os.path.basename(b))

    print("\n--- Gestion des sauvegardes (max 3 éligibles) ---")
    backup_mgr.manage_backups(max_backups=3)
    backups_after_manage = backup_mgr.list_backups()
    print("Sauvegardes restantes après gestion:")
    for b in backups_after_manage:
        print(os.path.basename(b))

    print("\n--- Restauration de la sauvegarde la plus récente ---")
    # Modifier le fichier original pour voir si la restauration fonctionne
    with open(dummy_db_path, "w") as f:
        f.write("Contenu modifié avant restauration.")
    print(f"Contenu DB avant restauration: {open(dummy_db_path).read()}")
    
    if backup_mgr.restore_backup():
        print(f"Contenu DB après restauration: {open(dummy_db_path).read()}")

    print("\n--- Restauration d'une sauvegarde spécifique (si elle existe encore) ---")
    if len(backups_after_manage) > 1:
        specific_backup_to_restore = os.path.basename(backups_after_manage[1]) # Essayer de restaurer la deuxième plus récente
        with open(dummy_db_path, "w") as f:
            f.write("Contenu re-modifié.")
        print(f"Contenu DB avant restauration spécifique: {open(dummy_db_path).read()}")
        if backup_mgr.restore_backup(specific_backup_to_restore):
            print(f"Contenu DB après restauration de {specific_backup_to_restore}: {open(dummy_db_path).read()}")
    
    # Nettoyage des fichiers de test
    print("\n--- Nettoyage ---")
    shutil.rmtree("data/test_backups")
    os.remove(dummy_db_path)
    print("Répertoire de sauvegarde de test et base de données factice supprimés.")

