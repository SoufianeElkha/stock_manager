# Documentation du Gestionnaire de Stock

## Nouvelles fonctionnalités

Cette mise à jour apporte trois améliorations majeures au Gestionnaire de Stock :

1. **Script de test complet** pour vérifier toutes les fonctionnalités avant la mise en production
2. **Système de sauvegarde automatique quotidienne** pour protéger vos données
3. **Sélection de l'emplacement de la base de données** au premier lancement

## 1. Script de test complet

Le script `comprehensive_test.py` permet de tester l'ensemble des fonctionnalités de l'application avant de la convertir en exécutable et de la déployer en production.

### Utilisation

```bash
python comprehensive_test.py
```

### Fonctionnalités testées

- Structure de la base de données
- Opérations CRUD (Create, Read, Update, Delete)
- Mouvements de stock
- Recherche d'articles
- Détection des articles à stock bas
- Insensibilité à la casse des références
- Gestion des références dupliquées
- Importation/exportation Excel
- Protection par mot de passe
- Opérations de base de données externe
- Mise en évidence des articles à stock bas dans l'interface

### Résultats

Le script affiche un résumé détaillé des tests effectués et indique clairement si l'application est prête pour la production.

## 2. Système de sauvegarde automatique

Le module `backup_manager.py` implémente un système de sauvegarde automatique quotidienne de la base de données.

### Caractéristiques

- **Sauvegarde automatique quotidienne** : Une sauvegarde est créée automatiquement chaque jour
- **Sauvegarde au démarrage** : Une sauvegarde est créée au démarrage de l'application si aucune n'a été faite le jour même
- **Rotation des sauvegardes** : Les anciennes sauvegardes sont supprimées automatiquement selon les règles configurées
- **Restauration facile** : Possibilité de restaurer une sauvegarde en cas de problème
- **Configuration personnalisable** : Paramètres ajustables via le fichier de configuration

### Configuration

Les paramètres de sauvegarde sont stockés dans le fichier `config/backup_config.ini` :

- `DatabasePath` : Chemin de la base de données à sauvegarder
- `BackupDirectory` : Répertoire où sont stockées les sauvegardes
- `RetentionDays` : Nombre de jours de conservation des sauvegardes (par défaut : 30)
- `IntervalHours` : Intervalle entre les sauvegardes en heures (par défaut : 24)
- `MaxBackups` : Nombre maximum de sauvegardes à conserver (par défaut : 100)

### Restauration manuelle

Pour restaurer manuellement une sauvegarde, vous pouvez utiliser le script suivant :

```python
from backup_manager import BackupManager

# Initialiser le gestionnaire de sauvegarde
backup_mgr = BackupManager()

# Lister les sauvegardes disponibles
backups = backup_mgr.list_backups()
for path, date in backups:
    print(f"{date}: {path}")

# Restaurer une sauvegarde
backup_path = backups[0][0]  # Première sauvegarde (la plus récente)
success, message = backup_mgr.restore_backup(backup_path)
if success:
    print(f"Restauration réussie: {message}")
else:
    print(f"Échec de la restauration: {message}")
```

## 3. Sélection de l'emplacement de la base de données

Le module `db_location_manager.py` permet à l'utilisateur de spécifier l'emplacement de la base de données au premier lancement de l'application.

### Fonctionnement

- Au premier lancement, une boîte de dialogue s'affiche pour demander l'emplacement de la base de données
- L'utilisateur peut sélectionner un répertoire où la base de données sera créée
- Si l'utilisateur annule, l'emplacement par défaut est utilisé (`data/stock_database.db`)
- L'emplacement choisi est enregistré dans le fichier de configuration et sera utilisé pour les lancements suivants

### Configuration manuelle

L'emplacement de la base de données est stocké dans le fichier `config/database_config.ini`. Vous pouvez modifier ce fichier manuellement si nécessaire :

```ini
[DATABASE]
Path = C:/chemin/vers/votre/base_de_donnees.db
```

### Réinitialisation

Pour forcer l'application à redemander l'emplacement de la base de données, vous pouvez supprimer le fichier de configuration ou exécuter le script suivant :

```python
from db_location_manager import DatabaseLocationManager

# Initialiser le gestionnaire d'emplacement
db_manager = DatabaseLocationManager()

# Configurer l'emplacement de la base de données
success, db_path = db_manager.setup_database_location()
if success:
    print(f"Base de données configurée: {db_path}")
else:
    print("Échec de la configuration")
```

## Utilisation de l'application mise à jour

1. Démarrez l'application avec la commande :
   ```bash
   python run_app.py
   ```

2. Au premier lancement, vous serez invité à sélectionner l'emplacement de la base de données.

3. L'application créera automatiquement une sauvegarde quotidienne de votre base de données.

4. Pour tester l'application avant de la convertir en exécutable, exécutez :
   ```bash
   python comprehensive_test.py
   ```

5. Pour vérifier l'intégration des nouvelles fonctionnalités, exécutez :
   ```bash
   python integration_test.py
   ```

## Conversion en exécutable

Pour convertir l'application en exécutable, utilisez le script `package_exe.py` mis à jour :

```bash
python package_exe.py
```

L'exécutable généré inclura toutes les nouvelles fonctionnalités et permettra à l'utilisateur de spécifier l'emplacement de la base de données au premier lancement.

## Dépannage

### La sauvegarde automatique ne fonctionne pas

1. Vérifiez que le répertoire de sauvegarde existe et est accessible en écriture
2. Vérifiez le fichier de log `logs/backup.log` pour plus d'informations
3. Assurez-vous que le chemin de la base de données est correctement configuré

### Erreur lors de la sélection de l'emplacement de la base de données

1. Assurez-vous que le répertoire sélectionné est accessible en écriture
2. Vérifiez que l'application a les droits nécessaires pour créer des fichiers
3. Si le problème persiste, l'application utilisera l'emplacement par défaut

### Restauration d'une sauvegarde

1. Fermez l'application avant de restaurer une sauvegarde
2. Utilisez le script de restauration fourni dans la documentation
3. Redémarrez l'application après la restauration

## Support

Pour toute question ou problème, contactez le support technique Swisspro.
