import os
import requests
from bs4 import BeautifulSoup

# URLs de las competiciones por categoría en la FNPV
URLS_COMPETICION = [
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3235"  # Alevín 1º
    # Iremos añadiendo las URLs del resto de categorías aquí separadas por comas
]

CLUB_BUSQUEDA = "ABAXITABIDEA"

def obtener_partidos_fnpv():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    }
    
    partidos_encontrados = {}

    for url in URLS_COMPETICION:
        print(f"Rastreando competición: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar las tablas de encuentros/jornadas
            tablas = soup.find_all('table')
            for tabla in tablas:
                filas = tabla.find_all('tr')
                for fila in filas:
                    celdas = [c.get_text(strip=True) for c in fila.find_all(['td', 'th'])]
                    
                    # Comprobar si la fila tiene la estructura de partido (5 columnas aproximadamente)
                    if len(celdas) >= 5:
                        fecha_hora = celdas[0] if celdas[0] else "--"
                        fronton = celdas[1] if celdas[1] else "--"
                        local = celdas[2]
                        visitante = celdas[4] if len(celdas) > 4 else "--"
                        
                        texto_fila = " ".join(celdas).upper()
                        
                        if CLUB_BUSQUEDA in texto_fila:
                            # Identificar quién es nuestro equipo y quién el rival
                            if CLUB_BUSQUEDA in local.upper():
                                equipo_nuestro = local
                                rival = visitante
                            else:
                                equipo_nuestro = visitante
                                rival = local
                            
                            # Guardar los datos indexados por el texto del equipo/pareja
                            partidos_encontrados[equipo_nuestro.lower()] = {
                                "aurkaria": rival,
                                "fronton": fronton,
                                "horario": fecha_hora
                            }
                            
        except Exception as e:
            print(f"Error procesando {url}: {e}")

    return partidos_encontrados

def actualizar_partidak_html(partidos_datos):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print(f"Error: No se encuentra {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    actualizados = 0

    # Recorrer las filas de las tablas en partidak.html
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 4:
            texto_pareja = tds[0].get_text(strip=True).lower()
            
            # Buscar coincidencia de los nombres de los pelotaris
            for equipo_fnpv, datos in partidos_datos.items():
                # Extraer apellidos o nombres para emparejar
                pelotaris = [p.strip().lower() for p in texto_pareja.replace('–', '-').split('-')]
                
                coincide = any(pelotari in equipo_fnpv for pelotari in pelotaris if len(pelotari) > 2)
                
                if coincide:
                    tds[1].string = datos["aurkaria"]
                    tds[2].string = datos["fronton"]
                    tds[3].string = datos["horario"]
                    actualizados += 1
                    break

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Proceso completado. Parejas actualizadas en partidak.html: {actualizados}")

if __name__ == "__main__":
    datos = obtener_partidos_fnpv()
    actualizar_partidak_html(datos)
