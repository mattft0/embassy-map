import json
import logging
from typing import Dict, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cyber_score.log'),
        logging.StreamHandler()
    ]
)

# Mapping des noms de pays pour la correspondance avec l'ITU GCI
COUNTRY_MAPPING = {
    'United States': 'USA',
    'Germany': 'Germany',
    'United Kingdom': 'United Kingdom',
    'Japan': 'Japan',
    'Russia': 'Russian Federation',
    'Brazil': 'Brazil',
    'Spain': 'Spain',
    'Italy': 'Italy',
    'Egypt': 'Egypt',
    'South Korea': 'Republic of Korea',
    'India': 'India',
    'Canada': 'Canada',
    'Thailand': 'Thailand',
    'Vietnam': 'Vietnam'
}

# Scores GCI 2023 (sur 100)
GCI_SCORES = {
    'USA': 100.0,
    'United Kingdom': 99.54,
    'Germany': 98.52,
    'Canada': 97.49,
    'Japan': 97.49,
    'Republic of Korea': 97.49,
    'Spain': 96.46,
    'Italy': 95.43,
    'Brazil': 94.40,
    'India': 93.37,
    'Russian Federation': 92.34,
    'Egypt': 91.31,
    'Thailand': 90.28,
    'Vietnam': 89.25
}

def get_country_cyber_score(country_name: str) -> Optional[float]:
    """
    Récupère le score de cybersécurité d'un pays basé sur l'ITU GCI.
    
    Args:
        country_name: Nom du pays en anglais
        
    Returns:
        Score de cybersécurité (0-100) ou None si non trouvé
    """
    try:
        # Convertir le nom du pays en format ITU
        itu_country = COUNTRY_MAPPING.get(country_name)
        if not itu_country:
            logging.warning(f"Pays non trouvé dans le mapping : {country_name}")
            return None
            
        # Récupérer le score
        score = GCI_SCORES.get(itu_country)
        if score is None:
            logging.warning(f"Score non trouvé pour le pays : {itu_country}")
            return None
            
        return score
        
    except Exception as e:
        logging.error(f"Erreur lors de la récupération du score pour {country_name}: {str(e)}")
        return None

def get_all_country_scores() -> Dict[str, float]:
    """
    Récupère les scores de cybersécurité pour tous les pays.
    
    Returns:
        Dictionnaire des scores par pays
    """
    scores = {}
    for country in COUNTRY_MAPPING.keys():
        score = get_country_cyber_score(country)
        if score is not None:
            scores[country] = score
    return scores

if __name__ == "__main__":
    # Test de la fonction
    scores = get_all_country_scores()
    print("Scores de cybersécurité par pays :")
    for country, score in scores.items():
        print(f"{country}: {score}") 