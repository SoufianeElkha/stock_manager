"""
Script de test d'intégration pour vérifier le bon fonctionnement des nouvelles fonctionnalités
- Test du système de sauvegarde automatique
- Test de la sélection de l'emplacement de la base de données
"""

import os
import sys
import unittest
import tempfile
import shutil
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import threading

# Ajouter le répertoire parent au chemin pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modules à tester
from backup_manager import BackupManager
from db_location_manager import DatabaseLocationManager

class TestBackupSystem(unittest.TestCase):
    """Tests pour le système de sauvegarde automatique"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        # Créer des répertoires temporaires
        self.temp_dir = tempfile.mkdtemp()
        self.db_dir = os.path.join(self.temp_dir, "db")
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.config_dir = os.path.join(self.temp_dir, "config")
        
        # Créer les répertoires
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Créer une base de données de test
        self.db_file = os.path.join(self.db_dir, "test_db.sqlite")
        self.create_test_database(self.db_file)
        
        # Fichier de configuration
        self.config_file = os.path.join(self.config_dir, "backup_config.ini")
        
        # Initialiser le gestionnaire de sauvegarde
        self.backup_manager = BackupManager(
            db_path=self.db_file,
            backup_dir=self.backup_dir,
            config_file=self.config_file
        )
        
        # Configurer pour des tests rapides
        self.backup_manager.backup_interval = 0.05  # 3 minutes en heures
        self.backup_manager.retention_days = 1
        self.backup_manager.max_backups = 5
        self.backup_manager.save_config()
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        # Arrêter la sauvegarde automatique si elle est en cours
        if hasattr(self, 'backup_manager') and self.backup_manager.backup_thread and self.backup_manager.backup_thread.is_alive():
            self.backup_manager.stop_automatic_backup()
        
        # Supprimer les répertoires temporaires
        shutil.rmtree(self.temp_dir)
    
    def create_test_database(self, db_file):
        """Crée une base de données de test"""
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Créer les tables
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
        
        # Ajouter quelques données de test
        cursor.execute('''
        INSERT INTO articles (reference, description, quantite, position, quantite_minimale)
        VALUES (?, ?, ?, ?, ?)
        ''', ("TEST001", "Article de test 1", 10, "A1", 5))
        
        cursor.execute('''
        INSERT INTO articles (reference, description, quantite, position, quantite_minimale)
        VALUES (?, ?, ?, ?, ?)
        ''', ("TEST002", "Article de test 2", 20, "B2", 10))
        
        # Valider les changements
        conn.commit()
        conn.close()
    
    def test_manual_backup(self):
        """Test de la création manuelle d'une sauvegarde"""
        # Créer une sauvegarde
        success, message, backup_path = self.backup_manager.create_backup()
        
        # Vérifier que la sauvegarde a réussi
        self.assertTrue(success)
        self.assertIsNotNone(backup_path)
        self.assertTrue(os.path.exists(backup_path))
        
        # Vérifier que la sauvegarde est une copie valide de la base de données
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # Vérifier que les tables existent
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        self.assertIn("articles", table_names)
        self.assertIn("mouvements", table_names)
        
        # Vérifier que les données sont présentes
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        conn.close()
    
    def test_automatic_backup(self):
        """Test de la sauvegarde automatique"""
        # Démarrer la sauvegarde automatique
        self.backup_manager.start_automatic_backup()
        
        # Attendre que la sauvegarde automatique se déclenche
        time.sleep(10)  # Attendre 10 secondes
        
        # Arrêter la sauvegarde automatique
        self.backup_manager.stop_automatic_backup()
        
        # Vérifier qu'au moins une sauvegarde a été créée
        backups = self.backup_manager.list_backups()
        self.assertGreater(len(backups), 0)
    
    def test_backup_rotation(self):
        """Test de la rotation des sauvegardes"""
        # Créer plus de sauvegardes que le maximum autorisé
        for i in range(10):
            self.backup_manager.create_backup()
        
        # Vérifier que le nombre de sauvegardes est limité
        backups = self.backup_manager.list_backups()
        self.assertLessEqual(len(backups), self.backup_manager.max_backups)
    
    def test_restore_backup(self):
        """Test de la restauration d'une sauvegarde"""
        # Créer une sauvegarde
        success, message, backup_path = self.backup_manager.create_backup()
        self.assertTrue(success)
        
        # Modifier la base de données originale
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM articles")
        conn.commit()
        conn.close()
        
        # Vérifier que la base de données est vide
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)
        conn.close()
        
        # Restaurer la sauvegarde
        success, message = self.backup_manager.restore_backup(backup_path)
        self.assertTrue(success)
        
        # Vérifier que les données ont été restaurées
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        conn.close()

class TestDatabaseLocationManager(unittest.TestCase):
    """Tests pour le gestionnaire d'emplacement de la base de données"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        # Créer des répertoires temporaires
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")
        
        # Créer les répertoires
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Fichier de configuration
        self.config_file = os.path.join(self.config_dir, "db_config.ini")
        
        # Initialiser le gestionnaire d'emplacement
        self.db_location_manager = DatabaseLocationManager(self.config_file)
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        # Supprimer les répertoires temporaires
        shutil.rmtree(self.temp_dir)
    
    def test_config_operations(self):
        """Test des opérations de configuration"""
        # Définir un chemin de base de données
        test_path = os.path.join(self.temp_dir, "test_db.sqlite")
        
        # Enregistrer le chemin
        success = self.db_location_manager.set_database_path(test_path)
        self.assertTrue(success)
        
        # Récupérer le chemin
        db_path = self.db_location_manager.get_database_path()
        self.assertEqual(db_path, test_path)
        
        # Vérifier que le fichier de configuration a été créé
        self.assertTrue(os.path.exists(self.config_file))
    
    def test_first_launch_detection(self):
        """Test de la détection du premier lancement"""
        # Au départ, c'est le premier lancement
        self.assertTrue(self.db_location_manager.is_first_launch())
        
        # Définir un chemin de base de données
        test_path = os.path.join(self.temp_dir, "test_db.sqlite")
        self.db_location_manager.set_database_path(test_path)
        
        # Créer une base de données vide
        conn = sqlite3.connect(test_path)
        conn.close()
        
        # Maintenant ce n'est plus le premier lancement
        self.assertFalse(self.db_location_manager.is_first_launch())
    
    def test_database_initialization(self):
        """Test de l'initialisation de la base de données"""
        # Définir un chemin de base de données
        test_path = os.path.join(self.temp_dir, "test_db.sqlite")
        
        # Initialiser la base de données
        success = self.db_location_manager.initialize_database(test_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(test_path))
        
        # Vérifier que la base de données a été correctement initialisée
        conn = sqlite3.connect(test_path)
        cursor = conn.cursor()
        
        # Vérifier que les tables existent
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        self.assertIn("articles", table_names)
        self.assertIn("mouvements", table_names)
        
        conn.close()

class TestIntegration(unittest.TestCase):
    """Tests d'intégration pour vérifier que les modules fonctionnent ensemble"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        # Créer des répertoires temporaires
        self.temp_dir = tempfile.mkdtemp()
        self.db_dir = os.path.join(self.temp_dir, "db")
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.config_dir = os.path.join(self.temp_dir, "config")
        
        # Créer les répertoires
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Fichiers de configuration
        self.db_config_file = os.path.join(self.config_dir, "db_config.ini")
        self.backup_config_file = os.path.join(self.config_dir, "backup_config.ini")
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        # Supprimer les répertoires temporaires
        shutil.rmtree(self.temp_dir)
    
    def test_db_location_and_backup_integration(self):
        """Test de l'intégration entre le gestionnaire d'emplacement et le système de sauvegarde"""
        # Initialiser le gestionnaire d'emplacement
        db_location_manager = DatabaseLocationManager(self.db_config_file)
        
        # Définir un chemin de base de données
        db_path = os.path.join(self.db_dir, "integration_test.sqlite")
        db_location_manager.set_database_path(db_path)
        
        # Initialiser la base de données
        db_location_manager.initialize_database(db_path)
        
        # Initialiser le gestionnaire de sauvegarde
        backup_manager = BackupManager(
            db_path=db_path,
            backup_dir=self.backup_dir,
            config_file=self.backup_config_file
        )
        
        # Créer une sauvegarde
        success, message, backup_path = backup_manager.create_backup()
        self.assertTrue(success)
        self.assertTrue(os.path.exists(backup_path))
        
        # Modifier la base de données
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO articles (reference, description, quantite, position, quantite_minimale)
        VALUES (?, ?, ?, ?, ?)
        ''', ("TEST001", "Article de test", 10, "A1", 5))
        conn.commit()
        conn.close()
        
        # Créer une autre sauvegarde
        success, message, backup_path2 = backup_manager.create_backup()
        self.assertTrue(success)
        
        # Vérifier que les deux sauvegardes sont différentes
        self.assertNotEqual(backup_path, backup_path2)
        
        # Restaurer la première sauvegarde
        success, message = backup_manager.restore_backup(backup_path)
        self.assertTrue(success)
        
        # Vérifier que la base de données a été restaurée
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)  # La première sauvegarde était vide
        conn.close()

def run_integration_tests():
    """Exécute tous les tests d'intégration"""
    # Créer une suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter toutes les classes de test
    suite.addTests(loader.loadTestsFromTestCase(TestBackupSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseLocationManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Afficher un résumé
    print("\n=== RÉSUMÉ DES TESTS D'INTÉGRATION ===")
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Réussites: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    # Afficher un message de bienvenue
    print("=== TEST D'INTÉGRATION DES NOUVELLES FONCTIONNALITÉS ===")
    print("Ce script teste l'intégration des nouvelles fonctionnalités:")
    print("- Système de sauvegarde automatique")
    print("- Sélection de l'emplacement de la base de données")
    print("Date d'exécution:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("\nDémarrage des tests...\n")
    
    # Exécuter les tests
    success = run_integration_tests()
    
    # Afficher un message de conclusion
    if success:
        print("\n✅ TOUS LES TESTS D'INTÉGRATION ONT RÉUSSI - Les nouvelles fonctionnalités sont prêtes!")
    else:
        print("\n❌ CERTAINS TESTS D'INTÉGRATION ONT ÉCHOUÉ - Veuillez corriger les problèmes avant la mise en production.")
    
    # Code de sortie
    sys.exit(0 if success else 1)
