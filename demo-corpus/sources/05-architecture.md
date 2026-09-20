# Architecture de la plateforme documentaire

## Services

L'interface React communique avec une API FastAPI. PostgreSQL conserve les métadonnées et pgvector les représentations vectorielles. MinIO stocke les documents originaux.

## Recherche

Chaque question est transformée en vecteur multilingue. La requête SQL limite d'abord les fragments aux rôles et équipes autorisés, puis calcule la similarité cosinus.

## Génération

LM Studio exécute le modèle de langage localement. Seuls les passages retenus et autorisés sont transmis au modèle avec leur titre et leur numéro de page.
