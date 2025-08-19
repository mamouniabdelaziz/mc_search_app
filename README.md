# Application de recherche – Concours Maître de Conférences / OFPPT

Cette application **Streamlit** permet de rechercher un **Nom** ou un **CIN** dans des résultats de concours
en important des fichiers **PDF/CSV/XLSX/JSON**. Elle réalise une **recherche approfondie** (exacte, partielle et floue)
et localise les occurrences dans les **PDF** avec **numéros de pages** et **extraits**.

## Installation

1. Installez Python 3.9+
2. Créez un environnement virtuel puis activez-le
3. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

## Lancement

```bash
streamlit run streamlit_app.py
```

Ouvrez ensuite l’URL locale indiquée par Streamlit (généralement http://localhost:8501).

## Utilisation

1. Importez les documents officiels (PDF des résultats, CSV/Excel, JSON).
2. Renseignez **Nom** et/ou **CIN** (barre latérale).
3. Ajustez le **seuil flou** si nécessaire.
4. Consultez :
   - le tableau des **correspondances tabulaires**
   - les **occurrences** trouvées dans les **PDF** (pages + extraits)
5. Exportez les résultats filtrés au format **CSV**.

> Remarques
> - Les PDF scannés en image ne sont pas lisibles sans OCR.
> - Pour de meilleurs résultats, téléchargez les **documents officiels** des universités/OFPPT et importez-les.

## Données d'exemple

Le dossier `sample_data/` contient des fichiers d'exemple (`sample_results.csv`, `sample_results.json`) pour tester l'interface.

Bon usage !
