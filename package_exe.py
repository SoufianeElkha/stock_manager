"""
Script pour empaqueter l'application de gestion de stock en fichier exécutable (.exe)
"""

import os
import sys
import shutil
import subprocess
import platform

def create_executable():
    """
    Crée un fichier exécutable (.exe) de l'application de gestion de stock
    en utilisant PyInstaller
    """
    print("Préparation de l'empaquetage de l'application en fichier exécutable...")
    
    # Vérifier si PyInstaller est installé
    try:
        import PyInstaller
        print("PyInstaller est déjà installé.")
    except ImportError:
        print("Installation de PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # Vérifier si pandas est installé (pour l'importation Excel)
    try:
        import pandas
        print("Pandas est déjà installé.")
    except ImportError:
        print("Installation de pandas...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pandas"], check=True)
    
    # Vérifier si openpyxl est installé (pour l'importation Excel)
    try:
        import openpyxl
        print("Openpyxl est déjà installé.")
    except ImportError:
        print("Installation de openpyxl...")
        subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl"], check=True)
    
    # Vérifier si colorama est installé (pour les couleurs dans la console)
    try:
        import colorama
        print("Colorama est déjà installé.")
    except ImportError:
        print("Installation de colorama...")
        subprocess.run([sys.executable, "-m", "pip", "install", "colorama"], check=True)
    
    # Créer le fichier de spécification PyInstaller
    create_spec_file()
    
    # Exécuter PyInstaller
    print("Création du fichier exécutable avec PyInstaller...")
    subprocess.run(["pyinstaller", "--clean", "stock_manager.spec"], check=True)
    
    print("Fichier exécutable créé avec succès!")
    print(f"Chemin: {os.path.abspath('dist/GestionnaireStock.exe')}")
    
    return os.path.abspath("dist/GestionnaireStock.exe")

def create_spec_file():
    """Crée le fichier de spécification PyInstaller"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pandas', 'openpyxl', 'colorama'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Ajouter les fichiers de données
a.datas += [('icon.ico', 'icon.ico', 'DATA')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GestionnaireStock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
"""
    
    with open("stock_manager.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print("Fichier de spécification PyInstaller (stock_manager.spec) créé.")

def create_icon():
    """Crée une icône simple pour l'application"""
    try:
        from PIL import Image, ImageDraw
        
        # Créer une image 256x256 avec un fond transparent
        img = Image.new('RGBA', (256, 256), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Dessiner un carré bleu pour représenter une boîte
        draw.rectangle([(50, 50), (206, 206)], fill=(41, 128, 185), outline=(52, 152, 219), width=4)
        
        # Dessiner une barre pour représenter un graphique
        draw.rectangle([(80, 120), (100, 180)], fill=(231, 76, 60))
        draw.rectangle([(120, 100), (140, 180)], fill=(46, 204, 113))
        draw.rectangle([(160, 80), (180, 180)], fill=(241, 196, 15))
        
        # Sauvegarder l'image au format ICO
        img.save('icon.ico')
        print("Icône créée avec succès.")
    except ImportError:
        print("Pillow n'est pas installé. Installation en cours...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)
        create_icon()
    except Exception as e:
        print(f"Erreur lors de la création de l'icône: {e}")
        # Créer un fichier vide comme solution de secours
        with open('icon.ico', 'wb') as f:
            f.write(b'')

def create_installer():
    """
    Crée un installateur pour l'application en utilisant NSIS
    (Non disponible dans l'environnement sandbox, mais le code est fourni pour référence)
    """
    print("La création d'un installateur nécessite NSIS, qui n'est pas disponible dans cet environnement.")
    print("Voici comment vous pourriez créer un installateur sur un système Windows:")
    
    nsis_script = """
    ; Script d'installation pour le Gestionnaire de Stock
    
    !include "MUI2.nsh"
    
    ; Informations générales
    Name "Gestionnaire de Stock"
    OutFile "GestionnaireStock_Setup.exe"
    InstallDir "$PROGRAMFILES\\GestionnaireStock"
    InstallDirRegKey HKCU "Software\\GestionnaireStock" ""
    RequestExecutionLevel admin
    
    ; Interface
    !define MUI_ABORTWARNING
    !define MUI_ICON "icon.ico"
    
    ; Pages
    !insertmacro MUI_PAGE_WELCOME
    !insertmacro MUI_PAGE_DIRECTORY
    !insertmacro MUI_PAGE_INSTFILES
    !insertmacro MUI_PAGE_FINISH
    
    ; Langues
    !insertmacro MUI_LANGUAGE "French"
    
    ; Section d'installation
    Section "Programme principal" SecMain
        SetOutPath "$INSTDIR"
        File /r "dist\\GestionnaireStock\\*.*"
        
        ; Créer les répertoires de données
        CreateDirectory "$INSTDIR\\data"
        CreateDirectory "$INSTDIR\\config"
        
        ; Créer un raccourci dans le menu Démarrer
        CreateDirectory "$SMPROGRAMS\\Gestionnaire de Stock"
        CreateShortcut "$SMPROGRAMS\\Gestionnaire de Stock\\Gestionnaire de Stock.lnk" "$INSTDIR\\GestionnaireStock.exe"
        
        ; Créer un raccourci sur le bureau
        CreateShortcut "$DESKTOP\\Gestionnaire de Stock.lnk" "$INSTDIR\\GestionnaireStock.exe"
        
        ; Enregistrer les informations de désinstallation
        WriteRegStr HKCU "Software\\GestionnaireStock" "" $INSTDIR
        WriteUninstaller "$INSTDIR\\Uninstall.exe"
        WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\GestionnaireStock" "DisplayName" "Gestionnaire de Stock"
        WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\GestionnaireStock" "UninstallString" "$INSTDIR\\Uninstall.exe"
        WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\GestionnaireStock" "DisplayIcon" "$INSTDIR\\GestionnaireStock.exe"
        WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\GestionnaireStock" "Publisher" "Votre Entreprise"
    SectionEnd
    
    ; Section de désinstallation
    Section "Uninstall"
        ; Supprimer les fichiers et répertoires
        RMDir /r "$INSTDIR"
        
        ; Supprimer les raccourcis
        Delete "$SMPROGRAMS\\Gestionnaire de Stock\\Gestionnaire de Stock.lnk"
        RMDir "$SMPROGRAMS\\Gestionnaire de Stock"
        Delete "$DESKTOP\\Gestionnaire de Stock.lnk"
        
        ; Supprimer les clés de registre
        DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\GestionnaireStock"
        DeleteRegKey HKCU "Software\\GestionnaireStock"
    SectionEnd
    """
    
    with open("installer.nsi", "w", encoding="utf-8") as f:
        f.write(nsis_script)
    
    print("Fichier de script NSIS (installer.nsi) créé.")
    print("Pour créer l'installateur, exécutez 'makensis installer.nsi' sur un système Windows avec NSIS installé.")

def create_readme():
    """Crée un fichier README avec des instructions d'utilisation"""
    readme_content = """# Gestionnaire de Stock

## Description
Cette application permet de gérer le stock de matériel de votre entreprise. Elle offre une interface moderne et intuitive pour ajouter, modifier et suivre vos articles.

## Fonctionnalités
- Gestion des articles avec référence, description, quantité et position
- Définition d'une quantité minimale pour chaque article avec alerte visuelle
- Ajout et retrait de stock avec suivi des mouvements
- Recherche d'articles par référence ou description
- Importation et exportation de données via Excel
- Export des articles à commander (quantité < minimum)
- Interface moderne entièrement en français

## Améliorations apportées
- Gestion des références dupliquées : Lorsque vous ajoutez un article avec une référence existante, l'application vous propose d'ajouter la quantité à l'article existant.
- Importation Excel : Vous pouvez importer des articles depuis un fichier Excel.
- Modification du retrait d'articles : Le champ "Commentaire" a été remplacé par "Projet" et un champ pour le nom du travailleur a été ajouté.
- Protection par mot de passe : Les fonctions d'importation et d'exportation sont protégées par le mot de passe "Swisspro24".
- Quantité minimale : Une colonne pour la quantité minimale a été ajoutée et les articles en dessous de ce seuil sont affichés en rouge.
- Export des articles à commander : Vous pouvez exporter la liste des articles dont la quantité est inférieure au minimum.
- Interface moderne : L'interface graphique a été modernisée avec un design plus attrayant.
- Majuscules automatiques : Toutes les références, noms de projets et noms d'utilisateurs sont automatiquement convertis en majuscules.
- Position des articles : Une colonne "Position" a été ajoutée pour indiquer l'emplacement de chaque article.

## Installation
1. Téléchargez le fichier `GestionnaireStock.exe`
2. Exécutez-le pour lancer l'application

## Utilisation
- **Ajouter un article**: Cliquez sur "Nouvel Article" et remplissez les informations
- **Modifier un article**: Sélectionnez un article et cliquez sur "Modifier"
- **Ajouter du stock**: Sélectionnez un article et cliquez sur "Ajouter Stock"
- **Retirer du stock**: Sélectionnez un article et cliquez sur "Retirer Stock"
- **Voir l'historique**: Sélectionnez un article et cliquez sur "Historique"
- **Importer depuis Excel**: Cliquez sur "Importer Excel" et sélectionnez votre fichier
- **Exporter les articles à commander**: Cliquez sur "Exporter à commander"

## Format du fichier Excel pour l'importation
Le fichier Excel doit contenir au minimum les colonnes suivantes :
- reference (obligatoire)
- description (obligatoire)
- quantite (optionnel)
- quantite_minimale (optionnel)
- position (optionnel)

## Support
Pour toute assistance, veuillez contacter le support technique.
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("Fichier README.md créé.")

def create_installation_guide():
    """Crée un guide d'installation"""
    guide_content = """# Guide d'installation du Gestionnaire de Stock

## Prérequis
- Système d'exploitation Windows 7/8/10/11
- 100 Mo d'espace disque disponible
- 2 Go de RAM minimum

## Installation simple
1. Téléchargez le fichier `GestionnaireStock.exe`
2. Double-cliquez sur le fichier pour lancer l'application
3. L'application créera automatiquement les répertoires nécessaires lors du premier lancement

## Installation avec l'installateur (si disponible)
1. Téléchargez le fichier `GestionnaireStock_Setup.exe`
2. Double-cliquez sur le fichier pour lancer l'installation
3. Suivez les instructions à l'écran
4. Une fois l'installation terminée, vous pouvez lancer l'application depuis le raccourci créé sur le bureau ou dans le menu Démarrer

## Configuration pour l'accès multi-utilisateurs
Pour permettre à plusieurs utilisateurs d'accéder à la même base de données:

1. Créez un dossier partagé sur le réseau accessible à tous les utilisateurs
2. Copiez le fichier de base de données (`data/stock_database.db`) dans ce dossier partagé
3. Dans l'application, allez dans le menu "Paramètres" et configurez le chemin vers la base de données partagée
4. Assurez-vous que tous les utilisateurs ont les droits d'accès en lecture et écriture sur ce dossier

## Dépannage
- Si l'application ne démarre pas, vérifiez que vous avez les droits d'administrateur
- Si vous rencontrez des erreurs lors de l'accès à la base de données, vérifiez les droits d'accès au dossier `data`
- Pour réinitialiser l'application, supprimez le dossier `data` et relancez l'application

## Désinstallation
1. Si vous avez utilisé l'installateur, utilisez le programme de désinstallation dans le Panneau de configuration
2. Si vous avez utilisé le fichier exécutable directement, supprimez simplement le fichier et les dossiers `data` et `config` associés
"""
    
    with open("INSTALLATION.md", "w", encoding="utf-8") as f:
        f.write(guide_content)
    
    print("Guide d'installation (INSTALLATION.md) créé.")

if __name__ == "__main__":
    # Créer l'icône de l'application
    create_icon()
    
    # Créer le fichier README et le guide d'installation
    create_readme()
    create_installation_guide()
    
    # Créer l'exécutable
    exe_path = create_executable()
    
    # Créer le script d'installation (pour référence)
    create_installer()
    
    print("\nProcessus d'empaquetage terminé!")
    print(f"Fichier exécutable: {exe_path}")
    print("Fichier README: README.md")
    print("Guide d'installation: INSTALLATION.md")
    print("Script d'installation: installer.nsi (pour référence)")
