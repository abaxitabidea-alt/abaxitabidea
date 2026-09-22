import os
import requests
from bs4 import BeautifulSoup

# URL de Competición FNPV
URL_FNPV = "https://www.fnpelota.com/pub/modalidadescompeticion.asp?idioma=ca&idCategoria=3204&temp=2026"
CLUB_BUSQUEDA = "ABAXITABIDEA"

def buscar_partidos_abaxitabidea():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    print(f"Buscando partidos para {CLUB_BUSQUEDA} en FNPV...")
    
    try:
        response = requests.get(URL_FNPV, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"Error al acceder a FNPV (Status: {response.status_code})")
            return {}

        soup = BeautifulSoup(response.text, 'html.parser')
        partidos_por_pareja = {}

        # Escanear todas las tablas de la FNPV
        for tabla in soup.find_all('table'):
            for fila in tabla.find_all('tr'):
                celdas = [c.get_text(strip=True) for c in fila.find_all(['td', 'th'])]
                texto_fila = " ".join(celdas).upper()
                
                if CLUB_BUSQUEDA in texto_fila:
                    # Intentar extraer información clave: Pareja, Aurkaria, Frontón, Hora
                    pareja = celdas[0] if len(celdas) > 0 else "--"
                    aurkaria = celdas[1] if len(celdas) > 1 else "--"
                    fronton = celdas[2] if len(celdas) > 2 else "--"
                    horario = celdas[3] if len(celdas) > 3 else "--"
                    
                    partidos_por_pareja[pareja.lower()] = {
                        "aurkaria": aurkaria,
                        "fronton": fronton,
                        "horario": horario
                    }

        return partidos_por_pareja

    except Exception as e:
        print(f"Error durante la búsqueda: {e}")
        return {}

def actualizar_partidak_html(datos_partidos):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} no existe.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    filas_modificadas = 0

    # Recorrer las filas de la tabla existente en partidak.html
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 4:
            nombre_pareja = tds[0].get_text(strip=True).lower()
            
            # Buscar si la pareja tiene datos actualizados de la FNPV
            for pareja_key, datos in datos_partidos.items():
                if pareja_key in nombre_pareja or nombre_pareja in pareja_key:
                    tds[1].string = datos["aurkaria"]
                    tds[2].string = datos["fronton"]
                    tds[3].string = datos["horario"]
                    filas_modificadas += 1
                    break

    # Guardar el HTML actualizado
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Proceso finalizado. Filas actualizadas en HTML: {filas_modificadas}")

if __name__ == "__main__":
    partidos = buscar_partidos_abaxitabidea()
    actualizar_partidak_html(partidos)
