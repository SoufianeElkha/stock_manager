#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script simplifié pour exécuter l'application Gestionnaire de Stock
Ce script crée une base de données initiale si elle n'existe pas
"""

import os
import sys
import sqlite3
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

def create_initial_database():
    """Crée une base de données initiale si elle n'existe pas"""
    # Créer le répertoire data s'il n'existe pas
    os.makedirs("data", exist_ok=True)
    
    # Chemin de la base de données
    db_path = os.path.join("data", "stock_database.db")
    
    # Vérifier si la base de données existe déjà
    if os.path.exists(db_path):
        print("La base de données existe déjà.")
        return
    
    print("Création d'une base de données initiale...")
    
    # Créer la base de données et les tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Créer la table articles avec les colonnes date_creation et date_modification
    cursor.execute('''
    CREATE TABLE articles (
        reference TEXT PRIMARY KEY,
        description TEXT,
        quantite INTEGER,
        position TEXT,
        quantite_minimale INTEGER,
        date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_modification TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Créer la table mouvements avec les noms de colonnes corrects
    cursor.execute('''
    CREATE TABLE mouvements (
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
    
    # Date actuelle pour les articles d'exemple
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Ajouter quelques articles d'exemple
    articles = [
        ('REF001', 'Câble électrique 3G1.5', 100, 'A1', 20, current_date, current_date),
        ('REF002', 'Disjoncteur 16A', 50, 'B2', 10, current_date, current_date),
        ('REF003', 'Prise murale', 75, 'C3', 15, current_date, current_date),
        ('REF004', 'Interrupteur simple', 60, 'D4', 12, current_date, current_date),
        ('REF005', 'Boîte de dérivation', 40, 'E5', 8, current_date, current_date)
    ]
    
    cursor.executemany('''
    INSERT INTO articles (reference, description, quantite, position, quantite_minimale, date_creation, date_modification)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', articles)
    
    # Valider les changements et fermer la connexion
    conn.commit()
    conn.close()
    
    print("Base de données initiale créée avec succès!")

def run_application():
    """Exécute l'application principale"""
    try:
        # Importer les modules de l'application
        from database_design import DatabaseManager
        from stock_functions import StockManager
        from gui_interface import ModernStockManagerApp
        
        # Créer la fenêtre principale
        root = tk.Tk()
        root.title("Gestionnaire de Stock - Swisspro")
        
        # Initialiser l'application
        app = ModernStockManagerApp(root)
        
        # Configurer la fermeture de l'application
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
        # Démarrer la boucle principale
        root.mainloop()
    
    except Exception as e:
        messagebox.showerror("Erreur", f"Une erreur est survenue lors du démarrage de l'application: {e}")
        raise

if __name__ == "__main__":
    # Créer une base de données initiale si nécessaire
    create_initial_database()
    
    # Exécuter l'application
    run_application()
