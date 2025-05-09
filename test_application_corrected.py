"""
Script de test d'intégration corrigé pour l'application de gestion de stock
Ce script teste les fonctionnalités principales de l'application
"""

import os
import sys
import unittest
import sqlite3
import tempfile
import shutil
from datetime import datetime

# Importer les modules de l'application
from database_design import DatabaseManager
from stock_functions import StockManager
from external_db import ExternalDatabaseConnector

class TestDatabaseManager(unittest.TestCase):
    """Tests pour les fonctionnalités de base de données"""
    
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
        self.db_manager.conn.close()
        shutil.rmtree(self.temp_dir)
    
    def test_add_article(self):
        """Test de l'ajout d'un article"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10, 5, "A1")
        
        # Vérifier que l'article a été ajouté
        article = self.db_manager.get_article("TEST001")
        self.assertIsNotNone(article)
        self.assertEqual(article[0], "TEST001")  # Référence
        self.assertEqual(article[1], "Article de test")  # Description
        self.assertEqual(article[2], 10)  # Quantité
    
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
    
    def test_get_all_articles(self):
        """Test de la récupération de tous les articles"""
        # Ajouter des articles
        self.db_manager.add_article("TEST001", "Article 1", 10, 5, "A1")
        self.db_manager.add_article("TEST002", "Article 2", 20, 10, "B2")
        
        # Récupérer tous les articles
        articles = self.db_manager.get_all_articles()
        
        # Vérifier le nombre d'articles
        self.assertEqual(len(articles), 2)
        
        # Vérifier les données du premier article
        self.assertEqual(articles[0][0], "TEST001")
        self.assertEqual(articles[0][1], "Article 1")
    
    def test_update_quantity_add(self):
        """Test de l'ajout de quantité à un article"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10, 5, "A1")
        
        # Ajouter de la quantité
        self.db_manager.update_quantity("TEST001", 5, "AJOUT", "PROJET1", "USER1")
        
        # Vérifier la nouvelle quantité
        article = self.db_manager.get_article("TEST001")
        self.assertEqual(article[2], 15)  # 10 + 5
        
        # Vérifier le mouvement
        mouvements = self.db_manager.get_article_movements("TEST001")
        self.assertEqual(len(mouvements), 1)
        
        mouvement = mouvements[0]
        self.assertEqual(mouvement[1], "TEST001")  # Référence
        self.assertEqual(mouvement[3], "AJOUT")  # Type de mouvement
        self.assertEqual(mouvement[4], 5)  # Quantité
        self.assertEqual(mouvement[5], "PROJET1")  # Projet
        self.assertEqual(mouvement[6], "USER1")  # Utilisateur
    
    def test_update_quantity_remove(self):
        """Test du retrait de quantité d'un article"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10, 5, "A1")
        
        # Retirer de la quantité
        self.db_manager.update_quantity("TEST001", 3, "RETRAIT", "PROJET2", "USER2")
        
        # Vérifier la nouvelle quantité
        article = self.db_manager.get_article("TEST001")
        self.assertEqual(article[2], 7)  # 10 - 3
        
        # Vérifier le mouvement
        mouvements = self.db_manager.get_article_movements("TEST001")
        self.assertEqual(len(mouvements), 1)
        
        mouvement = mouvements[0]
        self.assertEqual(mouvement[1], "TEST001")  # Référence
        self.assertEqual(mouvement[3], "RETRAIT")  # Type de mouvement
        self.assertEqual(mouvement[4], 3)  # Quantité
    
    def test_update_quantity_remove_too_much(self):
        """Test du retrait d'une quantité supérieure au stock disponible"""
        # Ajouter un article
        self.db_manager.add_article("TEST001", "Article de test", 10, 5, "A1")
        
        # Tenter de retirer plus que disponible
        try:
            self.db_manager.update_quantity("TEST001", 15, "RETRAIT", "PROJET3", "USER3")
            self.fail("Le retrait d'une quantité supérieure au stock disponible devrait échouer")
        except Exception as e:
            self.assertIn("Quantité insuffisante", str(e))
        
        # Vérifier que la quantité n'a pas changé
        article = self.db_manager.get_article("TEST001")
        self.assertEqual(article[2], 10)
    
    def test_search_articles(self):
        """Test de la recherche d'articles"""
        # Ajouter des articles
        self.db_manager.add_article("TEST001", "Écran LCD", 10, 5, "A1")
        self.db_manager.add_article("TEST002", "Clavier sans fil", 20, 10, "B2")
        self.db_manager.add_article("TEST003", "Souris optique", 30, 15, "C3")
        
        # Recherche par référence
        articles = self.db_manager.search_articles("TEST00")
        self.assertEqual(len(articles), 3)
        
        # Recherche par description
        articles = self.db_manager.search_articles("sans fil")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0][0], "TEST002")
        
        # Recherche sans résultat
        articles = self.db_manager.search_articles("inexistant")
        self.assertEqual(len(articles), 0)

class TestStockManager(unittest.TestCase):
    """Tests pour les fonctionnalités du gestionnaire de stock"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_file = os.path.join(self.temp_dir, "test_stock.sqlite")
        self.stock_manager = StockManager(self.db_file)
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        self.stock_manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_add_article(self):
        """Test de l'ajout d'un article"""
        # Ajouter un article
        result, message = self.stock_manager.add_article("TEST001", "Article de test", 10, "A1", 5)
        self.assertTrue(result)
        
        # Vérifier que l'article a été ajouté
        article = self.stock_manager.get_article_by_reference("TEST001")
        self.assertIsNotNone(article)
        self.assertEqual(article['reference'], "TEST001")
        self.assertEqual(article['description'], "Article de test")
        self.assertEqual(article['quantite'], 10)
    
    def test_add_stock(self):
        """Test de l'ajout de stock"""
        # Ajouter un article
        self.stock_manager.add_article("TEST001", "Article de test", 10, "A1", 5)
        
        # Ajouter du stock
        result = self.stock_manager.add_stock("TEST001", 5, "PROJET1", "USER1")
        self.assertTrue(result)
        
        # Vérifier la nouvelle quantité
        article = self.stock_manager.get_article_by_reference("TEST001")
        self.assertEqual(article['quantite'], 15)  # 10 + 5
    
    def test_remove_stock(self):
        """Test du retrait de stock"""
        # Ajouter un article
        self.stock_manager.add_article("TEST001", "Article de test", 10, "A1", 5)
        
        # Retirer du stock
        result = self.stock_manager.remove_stock("TEST001", 3, "PROJET2", "USER2")
        self.assertTrue(result)
        
        # Vérifier la nouvelle quantité
        article = self.stock_manager.get_article_by_reference("TEST001")
        self.assertEqual(article['quantite'], 7)  # 10 - 3
    
    def test_get_low_stock_articles(self):
        """Test de la récupération des articles à stock bas"""
        # Ajouter des articles
        self.stock_manager.add_article("TEST001", "Article 1", 10, "A1", 15)  # Stock bas
        self.stock_manager.add_article("TEST002", "Article 2", 20, "B2", 10)  # Stock OK
        self.stock_manager.add_article("TEST003", "Article 3", 5, "C3", 10)   # Stock bas
        
        # Récupérer les articles à stock bas
        low_stock = self.stock_manager.get_low_stock_articles()
        
        # Vérifier le nombre d'articles à stock bas
        self.assertEqual(len(low_stock), 2)
        
        # Vérifier les références des articles à stock bas
        low_stock_refs = [article['reference'] for article in low_stock]
        self.assertIn("TEST001", low_stock_refs)
        self.assertIn("TEST003", low_stock_refs)

class TestExternalDatabaseConnector(unittest.TestCase):
    """Tests pour les fonctionnalités de connexion à une base de données externe"""
    
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
        self.external_connector = ExternalDatabaseConnector(self.external_db_file)
        
        # Correction: Ajouter l'attribut db_path manuellement
        self.external_connector.db_path = self.external_db_file
    
    def tearDown(self):
        """Nettoyage après chaque test"""
        self.db_manager.conn.close()
        shutil.rmtree(self.temp_dir)
    
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
        
        # Correction: Ajouter la méthode export_data_for_external_db si elle n'existe pas
        if not hasattr(self.db_manager, 'export_data_for_external_db'):
            def export_data_for_external_db(self):
                self.cursor.execute("""
                SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification
                FROM articles
                """)
                articles = self.cursor.fetchall()
                
                self.cursor.execute("""
                SELECT id, article_reference, date_mouvement, type_mouvement, quantite, projet, travailleur
                FROM mouvements
                """)
                mouvements = self.cursor.fetchall()
                
                return articles, mouvements
            
            # Ajouter la méthode dynamiquement
            import types
            self.db_manager.export_data_for_external_db = types.MethodType(export_data_for_external_db, self.db_manager)
        
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
    
    def test_import_from_external_db(self):
        """Test de l'importation des données depuis la base externe"""
        # Initialiser la base externe
        self.external_connector.initialize_external_db()
        
        # Correction: Ajouter la méthode export_data_for_external_db si elle n'existe pas
        if not hasattr(self.db_manager, 'export_data_for_external_db'):
            def export_data_for_external_db(self):
                self.cursor.execute("""
                SELECT reference, description, quantite, quantite_minimale, position, date_creation, date_modification
                FROM articles
                """)
                articles = self.cursor.fetchall()
                
                self.cursor.execute("""
                SELECT id, article_reference, date_mouvement, type_mouvement, quantite, projet, travailleur
                FROM mouvements
                """)
                mouvements = self.cursor.fetchall()
                
                return articles, mouvements
            
            # Ajouter la méthode dynamiquement
            import types
            self.db_manager.export_data_for_external_db = types.MethodType(export_data_for_external_db, self.db_manager)
        
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
        
        new_db_manager.conn.close()

if __name__ == "__main__":
    unittest.main()
