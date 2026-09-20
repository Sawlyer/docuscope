# Corpus NovaSphere

Documents entièrement fictifs destinés à valider recherche sémantique, citations par page et séparation des accès.

## Documents

- `01-organigramme.pdf` : direction générale et comité exécutif.
- `02-politique-rh.pdf` : entretiens, congés et intégration.
- `03-teletravail.pdf` : rythme, sécurité et équipement.
- `04-securite.pdf` : accès, secrets et incidents.
- `05-architecture.pdf` : composants et règle ACL avant recherche.
- `06-finance.pdf` : résultats T2 et prévision.
- `07-commercial.pdf` : cycle de vente et renouvellement.
- `08-contrat-confidentiel.pdf` : conditions sensibles accord Atlas.

## Protocole rapide

1. Importer PDF depuis compte administrateur.
2. Donner accès organigramme à Administrateur, politique RH à équipe RH, finance à équipe Finance, contrat à Direction.
3. Poser questions listées dans README racine.
4. Vérifier titre, page, extrait, score et ouverture fichier.
5. Refaire questions avec compte non autorisé et confirmer zéro source.

PDF reconstruits depuis sources Markdown avec :

```powershell
python scripts/build_demo_corpus.py
```
