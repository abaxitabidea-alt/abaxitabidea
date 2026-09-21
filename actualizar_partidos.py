import os
import requests
from bs4 import BeautifulSoup

# URL de la Federación Navarra de Pelota Vasca
URL_FNPV = "https://www.fnpelota.com/pub/modalidadescompeticion.asp?idioma=ca&idCategoria=3204&temp=2026"

def obtener_partidos():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(URL_FNPV, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            print(f"Error al acceder a la FNPV: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Aquí procesaremos las tablas cuando la FNPV publique los partidos.
        # Por ahora devolvemos la estructura preparada.
        partidos = []
        return partidos
    except Exception as e:
        print(f"Excepción durante el scraping: {e}")
        return []

if __name__ == "__main__":
    print("Iniciando búsqueda de partidos en FNPV...")
    partidos_encontrados = obtener_partidos()
    print(f"Partidos encontrados para Abaxitabidea: {len(partidos_encontrados)}")
