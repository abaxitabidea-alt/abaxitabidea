import os
import requests
from bs4 import BeautifulSoup

# URL de Competición FNPV
URL_FNPV = "https://www.fnpelota.com/pub/modalidadescompeticion.asp?idioma=ca&idCategoria=3204&temp=2026"

# Club y parejas de Abaxitabidea para rastrear
CLUB_BUSQUEDA = "ABAXITABIDEA"
PAREJAS_ABAXITABIDEA = [
    "U.Oteiza – I.Zubieta",
    "O.Mendioroz – T.Berruezo",
    "M.Dallo – M.Amorena",
    "O.Pérez de Obanos – M.Pérez de Obanos",
    "H.Astibia – A.Echeverria",
    "E.Petrox – E.Narvaez",
    "A.Ripodas – E.San Martin",
    "O.Atondo – A.Hazas",
    "I.Iltzarbe – U.Fillat",
    "E.Astibia – I.Petrox",
    "J.Amorena – M.Casajus",
    "P.Aginaga – X.Goldaracena"
]

def buscar_partidos_abaxitabidea():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    print(f"Buscando señalamientos oficiales para {CLUB_BUSQUEDA} en FNPV...")
    
    try:
        response = requests.get(URL_FNPV, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"Error al acceder a la FNPV (Status Code: {response.status_code})")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        partidos_encontrados = []
        
        # Escaneo de tablas en la web
        tablas = soup.find_all('table')
        for tabla in tablas:
            texto_tabla = tabla.get_text().lower()
            if CLUB_BUSQUEDA.lower() in texto_tabla:
                filas = tabla.find_all('tr')
                for fila in filas:
                    celdas = [c.get_text(strip=True) for c in fila.find_all(['td', 'th'])]
                    if any(CLUB_BUSQUEDA.lower() in c.lower() for c in celdas):
                        partidos_encontrados.append(celdas)

        if not partidos_encontrados:
            print(f"Aún no hay publicaciones en formato tabla para {CLUB_BUSQUEDA}.")
            
        return partidos_encontrados

    except Exception as e:
        print(f"Error durante el scraping: {e}")
        return []

def actualizar_partidak_html(partidos):
    if not os.path.exists("partidak.html"):
        print("Error: partidak.html no existe.")
        return

    print(f"Proceso finalizado. Partidos procesados: {len(partidos)}")

if __name__ == "__main__":
    partidos = buscar_partidos_abaxitabidea()
    actualizar_partidak_html(partidos)
