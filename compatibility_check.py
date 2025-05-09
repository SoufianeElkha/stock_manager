"""
Script de vérification de compatibilité pour les tests corrigés
Ce script vérifie que les tests corrigés sont compatibles avec l'application existante
"""

import os
import sys
import unittest
import importlib.util
import tempfile
import shutil

def import_module_from_file(module_name, file_path):
    """Importe un module Python à partir d'un fichier"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def run_tests_from_module(module):
    """Exécute les tests d'un module"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(module)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)

def check_compatibility():
    """Vérifie la compatibilité des tests corrigés avec l'application existante"""
    print("=== VÉRIFICATION DE COMPATIBILITÉ DES TESTS CORRIGÉS ===")
    
    # Créer un répertoire temporaire pour les tests
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Copier les fichiers nécessaires dans le répertoire temporaire
        # (Cette partie serait implémentée dans un environnement réel)
        
        # Importer les modules de test corrigés
        test_app_module = import_module_from_file("test_application", "test_application_corrected.py")
        comprehensive_test_module = import_module_from_file("comprehensive_test", "comprehensive_test_corrected.py")
        
        # Exécuter les tests d'intégration
        print("\n=== EXÉCUTION DES TESTS D'INTÉGRATION ===")
        test_app_result = run_tests_from_module(test_app_module)
        
        # Exécuter les tests complets
        print("\n=== EXÉCUTION DES TESTS COMPLETS ===")
        comprehensive_test_result = run_tests_from_module(comprehensive_test_module)
        
        # Vérifier les résultats
        test_app_success = test_app_result.wasSuccessful()
        comprehensive_test_success = comprehensive_test_result.wasSuccessful()
        
        # Afficher le résultat global
        print("\n=== RÉSULTAT DE LA VÉRIFICATION DE COMPATIBILITÉ ===")
        if test_app_success and comprehensive_test_success:
            print("✅ Les tests corrigés sont compatibles avec l'application existante.")
            return True
        else:
            print("❌ Certains tests corrigés ne sont pas compatibles avec l'application existante.")
            return False
    
    finally:
        # Nettoyer le répertoire temporaire
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    check_compatibility()
