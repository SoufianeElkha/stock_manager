"""
Script de test de compatibilité pour vérifier les corrections apportées
"""

import os
import sys
import unittest
import tempfile
import shutil
import sqlite3
from datetime import datetime

# Ajouter le répertoire parent au chemin de recherche
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modules corrigés
from database_design_fixed import DatabaseManager
from external_db_fixed import ExternalDatabaseConnector

class TestDatabaseManagerFixed(unittest.TestCase):
    """Tests pour les fonctionnalités de base de données corrigées"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        # Créer une base de données temporaire
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "test_db.sqlite")
        self.db_manager = DatabaseManager(self.db_file)
        self.db_manager.connect()
        self.db_manager.create_tables()
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        self.db_manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_add_duplicate_article(self):
        """Test de l'ajout d'un article avec une référence existante"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10, 5, "A1")
        
        # Tenter d'ajouter un article avec la même référence
        try:
            self.db_manager.add_article("TEST001", "Article dupliqué", 5, 2, "B2")
            self.fail("L'ajout d'un article avec une référence existante devrait échouer")
        except Exception as e:
            self.assertIn("UNIQUE constraint failed", str(e))
    
    def test_update_quantity_remove_too_much(self):
        """Test du retrait d'une quantité supérieure au stock disponible"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10, 5, "A1")
        
        # Tenter de retirer plus que disponible
        try:
            self.db_manager.update_quantity("TEST001", 15, "RETRAIT", "PROJET3", "USER3")
            self.fail("Le retrait d'une quantité supérieure au stock disponible devrait échouer")
        except ValueError as e:
            self.assertIn("Quantité insuffisante", str(e))
        
        # Vérifier que la quantité n'a pas changé
        article = self.db_manager.get_article("TEST001")
        self.assertEqual(article[2], 10)
    
    def test_export_data_for_external_db(self):
        """Test de l'exportation des données pour une base externe"""
        # Ajouter des articles
        self.db_manager.add_article("TEST001", "Article 1", 10, 5, "A1")
        self.db_manager.add_article("TEST002", "Article 2", 20, 10, "B2")
        
        # Ajouter des mouvements
        self.db_manager.update_quantity("TEST001", 5, "AJOUT", "PROJET1", "USER1")
        self.db_manager.update_quantity("TEST002", 3, "RETRAIT", "PROJET2", "USER2")
        
        # Exporter les données
        articles, mouvements = self.db_manager.export_data_for_external_db()
        
        # Vérifier les articles exportés
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0][0], "TEST001")
        self.assertEqual(articles[1][0], "TEST002")
        
        # Vérifier les mouvements exportés
        self.assertEqual(len(mouvements), 2)
        self.assertEqual(mouvements[0][1], "TEST001")
        self.assertEqual(mouvements[0][3], "AJOUT")
        self.assertEqual(mouvements[1][1], "TEST002")
        self.assertEqual(mouvements[1][3], "RETRAIT")

class TestExternalDatabaseConnectorFixed(unittest.TestCase):
    """Tests pour les fonctionnalités de connexion à une base de données externe corrigées"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.temp_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.db_file = os.path.join(self.data_dir, "test_db.sqlite")
        self.external_db_file = os.path.join(self.data_dir, "external_db.sqlite")
        
        self.db_manager = DatabaseManager(self.db_file)
        self.db_manager.connect()
        self.db_manager.create_tables()
        
        # Ajouter des données de test
        self.db_manager.add_article("TEST001", "Article 1", 10, 5, "A1")
        self.db_manager.add_article("TEST002", "Article 2", 20, 10, "B2")
        
        # Initialiser le connecteur de base de données externe
        self.external_connector = ExternalDatabaseConnector(os.path.join(self.temp_dir, "config.ini"))
        self.external_connector.external_db_path = self.external_db_file
        self.external_connector.db_path = self.external_db_file
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        self.db_manager.close()
        try:
            shutil.rmtree(self.temp_dir)
        except PermissionError:
            print(f"Impossible de supprimer {self.temp_dir}, il sera supprimé plus tard")
    
    def test_initialize_external_db(self):
        """Test de l'initialisation de la base de données externe"""
        # Initialiser la base externe
        result = self.external_connector.initialize_external_db()
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.external_db_file))
        
        # Vérifier la structure de la base externe
        conn = sqlite3.connect(self.external_db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        self.assertIn("articles", table_names)
        self.assertIn("mouvements", table_names)
        
        conn.close()
    
    def test_export_to_external_db(self):
        """Test de l'exportation des données vers la base externe"""
        # Initialiser la base externe
        self.external_connector.initialize_external_db()
        
        # Exporter vers la base externe
        result = self.external_connector.export_to_external_db(self.db_manager)
        self.assertTrue(result)
        
        # Vérifier l'export
        conn = sqlite3.connect(self.external_db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        conn.close()
    
    def test_import_to_local_db(self):
        """Test de l'importation des données depuis la base externe"""
        # Initialiser la base externe
        self.external_connector.initialize_external_db()
        
        # Exporter vers la base externe
        self.external_connector.export_to_external_db(self.db_manager)
        
        # Créer une nouvelle base locale vide
        new_db_file = os.path.join(self.data_dir, "new_db.sqlite")
        new_db_manager = DatabaseManager(new_db_file)
        new_db_manager.connect()
        new_db_manager.create_tables()
        
        # Importer depuis la base externe
        result = self.external_connector.import_to_local_db(new_db_manager)
        self.assertTrue(result)
        
        # Vérifier l'import
        new_db_manager.cursor.execute("SELECT COUNT(*) FROM articles")
        count = new_db_manager.cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        new_db_manager.close()

if __name__ == "__main__":
    unittest.main()
