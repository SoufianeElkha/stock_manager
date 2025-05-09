"""
Script de test pour l'application de gestion de stock
"""

import os
import sys
import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path

# Ajouter le répertoire parent au chemin pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_design import DatabaseManager
from stock_functions import StockManager
from external_db import ExternalDatabaseConnector

class TestDatabaseManager(unittest.TestCase):
    """Tests pour le gestionnaire de base de données"""
    
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
    
    def test_add_article(self):
        """Test de l'ajout d'un article"""
        # Ajouter un article
        result = self.db_manager.add_article("TEST001", "Article de test", 10)
        self.assertTrue(result)
        
        # Vérifier que l'article a été ajouté
        self.db_manager.cursor.execute("SELECT * FROM articles WHERE reference = ?", ("TEST001",))
        article = self.db_manager.cursor.fetchone()
        self.assertIsNotNone(article)
        self.assertEqual(article[1], "TEST001")
        self.assertEqual(article[2], "Article de test")
        self.assertEqual(article[3], 10)
    
    def test_add_duplicate_article(self):
        """Test de l'ajout d'un article avec une référence existante"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10)
        
        # Tenter d'ajouter un article avec la même référence
        result = self.db_manager.add_article("TEST001", "Autre article", 5)
        self.assertFalse(result)
    
    def test_update_quantity_add(self):
        """Test de l'ajout de quantité à un article"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10)
        
        # Ajouter de la quantité
        result = self.db_manager.update_quantity("TEST001", 5, "AJOUT", "testuser", "Test ajout")
        self.assertTrue(result)
        
        # Vérifier que la quantité a été mise à jour
        self.db_manager.cursor.execute("SELECT quantite FROM articles WHERE reference = ?", ("TEST001",))
        quantite = self.db_manager.cursor.fetchone()[0]
        self.assertEqual(quantite, 15)
        
        # Vérifier que le mouvement a été enregistré
        self.db_manager.cursor.execute("SELECT * FROM mouvements")
        mouvement = self.db_manager.cursor.fetchone()
        self.assertIsNotNone(mouvement)
        self.assertEqual(mouvement[2], "AJOUT")
        self.assertEqual(mouvement[3], 5)
        self.assertEqual(mouvement[5], "testuser")
        self.assertEqual(mouvement[6], "Test ajout")
    
    def test_update_quantity_remove(self):
        """Test du retrait de quantité d'un article"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10)
        
        # Retirer de la quantité
        result = self.db_manager.update_quantity("TEST001", 3, "RETRAIT", "testuser", "Test retrait")
        self.assertTrue(result)
        
        # Vérifier que la quantité a été mise à jour
        self.db_manager.cursor.execute("SELECT quantite FROM articles WHERE reference = ?", ("TEST001",))
        quantite = self.db_manager.cursor.fetchone()[0]
        self.assertEqual(quantite, 7)
    
    def test_update_quantity_remove_too_much(self):
        """Test du retrait d'une quantité supérieure au stock disponible"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10)
        
        # Tenter de retirer plus que la quantité disponible
        result = self.db_manager.update_quantity("TEST001", 15, "RETRAIT", "testuser", "Test retrait")
        self.assertFalse(result)
        
        # Vérifier que la quantité n'a pas été modifiée
        self.db_manager.cursor.execute("SELECT quantite FROM articles WHERE reference = ?", ("TEST001",))
        quantite = self.db_manager.cursor.fetchone()[0]
        self.assertEqual(quantite, 10)
    
    def test_get_all_articles(self):
        """Test de la récupération de tous les articles"""
        # Ajouter quelques articles
        self.db_manager.add_article("TEST001", "Article 1", 10)
        self.db_manager.add_article("TEST002", "Article 2", 20)
        self.db_manager.add_article("TEST003", "Article 3", 30)
        
        # Récupérer tous les articles
        articles = self.db_manager.get_all_articles()
        self.assertEqual(len(articles), 3)
    
    def test_search_articles(self):
        """Test de la recherche d'articles"""
        # Ajouter quelques articles
        self.db_manager.add_article("TEST001", "Écran LCD", 10)
        self.db_manager.add_article("TEST002", "Clavier sans fil", 20)
        self.db_manager.add_article("TEST003", "Souris sans fil", 30)
        
        # Rechercher des articles contenant "sans fil"
        articles = self.db_manager.search_articles("sans fil")
        self.assertEqual(len(articles), 2)
        
        # Rechercher des articles par référence
        articles = self.db_manager.search_articles("TEST001")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0][1], "TEST001")

class TestStockManager(unittest.TestCase):
    """Tests pour le gestionnaire de stock"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        # Créer une base de données temporaire
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "test_stock.sqlite")
        self.stock_manager = StockManager(self.db_file)
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        self.stock_manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_add_article(self):
        """Test de l'ajout d'un article"""
        result = self.stock_manager.add_article("TEST001", "Article de test", 10)
        self.assertTrue(result)
        
        # Vérifier que l'article a été ajouté
        article = self.stock_manager.get_article_by_reference("TEST001")
        self.assertIsNotNone(article)
        self.assertEqual(article[1], "TEST001")
        self.assertEqual(article[2], "Article de test")
        self.assertEqual(article[3], 10)
    
    def test_add_stock(self):
        """Test de l'ajout de stock"""
        # Ajouter un article
        self.stock_manager.add_article("TEST001", "Article de test", 10)
        
        # Ajouter du stock
        result = self.stock_manager.add_stock("TEST001", 5, "testuser", "Test ajout")
        self.assertTrue(result)
        
        # Vérifier que le stock a été mis à jour
        article = self.stock_manager.get_article_by_reference("TEST001")
        self.assertEqual(article[3], 15)
    
    def test_remove_stock(self):
        """Test du retrait de stock"""
        # Ajouter un article
        self.stock_manager.add_article("TEST001", "Article de test", 10)
        
        # Retirer du stock
        result = self.stock_manager.remove_stock("TEST001", 3, "testuser", "Test retrait")
        self.assertTrue(result)
        
        # Vérifier que le stock a été mis à jour
        article = self.stock_manager.get_article_by_reference("TEST001")
        self.assertEqual(article[3], 7)
    
    def test_get_low_stock_articles(self):
        """Test de la récupération des articles à stock bas"""
        # Ajouter quelques articles
        self.stock_manager.add_article("TEST001", "Article 1", 3)
        self.stock_manager.add_article("TEST002", "Article 2", 7)
        self.stock_manager.add_article("TEST003", "Article 3", 12)
        
        # Récupérer les articles à stock bas (seuil = 5)
        low_stock = self.stock_manager.get_low_stock_articles(5)
        self.assertEqual(len(low_stock), 1)
        self.assertEqual(low_stock[0][1], "TEST001")
        
        # Récupérer les articles à stock bas (seuil = 10)
        low_stock = self.stock_manager.get_low_stock_articles(10)
        self.assertEqual(len(low_stock), 2)

class TestExternalDatabaseConnector(unittest.TestCase):
    """Tests pour le connecteur de base de données externe"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        # Créer des répertoires temporaires
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.temp_dir, "data")
        self.config_dir = os.path.join(self.temp_dir, "config")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Créer les fichiers de base de données
        self.local_db_file = os.path.join(self.data_dir, "local_db.sqlite")
        self.external_db_file = os.path.join(self.data_dir, "external_db.sqlite")
        self.config_file = os.path.join(self.config_dir, "test_config.ini")
        
        # Initialiser le gestionnaire de base de données locale
        self.local_db = DatabaseManager(self.local_db_file)
        self.local_db.connect()
        self.local_db.create_tables()
        
        # Initialiser le connecteur de base de données externe
        self.external_connector = ExternalDatabaseConnector(self.config_file)
        self.external_connector.update_config("DATABASE", "Path", self.external_db_file)
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        self.local_db.close()
        shutil.rmtree(self.temp_dir)
    
    def test_initialize_external_db(self):
        """Test de l'initialisation de la base de données externe"""
        result = self.external_connector.initialize_external_db()
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.external_db_file))
        
        # Vérifier que les tables ont été créées
        conn = sqlite3.connect(self.external_db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        self.assertIn("articles", table_names)
        self.assertIn("mouvements", table_names)
        self.assertIn("sync_log", table_names)
        
        conn.close()
    
    def test_export_to_external_db(self):
        """Test de l'exportation des données vers la base externe"""
        # Ajouter des données à la base locale
        self.local_db.add_article("TEST001", "Article 1", 10)
        self.local_db.add_article("TEST002", "Article 2", 20)
        self.local_db.update_quantity("TEST001", 5, "AJOUT", "testuser", "Test")
        
        # Initialiser la base externe
        self.external_connector.initialize_external_db()
        
        # Exporter les données
        result = self.external_connector.export_to_external_db(self.local_db)
        self.assertTrue(result)
        
        # Vérifier que les données ont été exportées
        conn = sqlite3.connect(self.external_db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM articles")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        cursor.execute("SELECT COUNT(*) FROM mouvements")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
        
        conn.close()
    
    def test_import_from_external_db(self):
        """Test de l'importation des données depuis la base externe"""
        # Ajouter des données à la base locale et les exporter
        self.local_db.add_article("TEST001", "Article 1", 10)
        self.local_db.add_article("TEST002", "Article 2", 20)
        
        self.external_connector.initialize_external_db()
        self.external_connector.export_to_external_db(self.local_db)
        
        # Modifier la base locale
        self.local_db.cursor.execute("DELETE FROM articles")
        self.local_db.conn.commit()
        
        # Importer les données depuis la base externe
        result = self.external_connector.import_from_external_db(self.local_db)
        self.assertTrue(result)
        
        # Vérifier que les données ont été importées
        articles = self.local_db.get_all_articles()
        self.assertEqual(len(articles), 2)

def run_tests():
    """Exécute tous les tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseManager))
    suite.addTests(loader.loadTestsFromTestCase(TestStockManager))
    suite.addTests(loader.loadTestsFromTestCase(TestExternalDatabaseConnector))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
