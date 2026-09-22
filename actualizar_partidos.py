import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# URLs de las competiciones de la FNPV
URLS_COMPETICION = [
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3235"  # Alevín 1º
]

CLUB_BUSQUEDA = "ABAXITABIDEA"

def extraer_partidos_con_navegador():
    partidos_encontrados = {}
    
    with sync_playwright() as p:
        # Lanzar un navegador Chromium real en segundo plano
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for url in URLS_COMPETICION:
            print(f"Navegando a: {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                # Esperar a que se cargue la tabla de partidos
                page.wait_for_selector("table", timeout=10000)
                
                html_contenido = page.content()
                soup = BeautifulSoup(html_contenido, 'html.parser')
                
                for tabla in soup.find_all('table'):
                    for fila in tabla.find_all('tr'):
                        celdas = [c.get_text(strip=True) for c in fila.find_all(['td', 'th'])]
                        
                        if len(celdas) >= 5:
                            fecha_hora = celdas[0] if celdas[0] else "--"
                            fronton = celdas[1] if celdas[1] else "--"
                            local = celdas[2]
                            visitante = celdas[4] if len(celdas) > 4 else "--"
                            
                            texto_fila = " ".join(celdas).upper()
                            
                            if CLUB_BUSQUEDA in texto_fila:
                                if CLUB_BUSQUEDA in local.upper():
                                    equipo_nuestro = local
                                    rival = visitante
                                else:
                                    equipo_nuestro = visitante
                                    rival = local
                                
                                partidos_encontrados[equipo_nuestro.lower()] = {
                                    "aurkaria": rival,
                                    "fronton": fronton,
                                    "horario": fecha_hora
                                }
            except Exception as e:
                print(f"Error procesando {url}: {e}")
                
        browser.close()
        
    return partidos_encontrados

def actualizar_partidak_html(partidos_datos):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print("Error: partidak.html no existe.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    actualizados = 0

    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 4:
            texto_pareja = tds[0].get_text(strip=True).lower()
            
            for equipo_fnpv, datos in partidos_datos.items():
                pelotaris = [p.strip().lower() for p in re.split(r'[–-]', texto_pareja)]
                
                # Coincidencia por apellidos o nombres de los pelotaris
                if any(pelotari in equipo_fnpv for pelotari in pelotaris if len(pelotari) > 2):
                    tds[1].string = datos["aurkaria"]
                    tds[2].string = datos["fronton"]
                    tds[3].string = datos["horario"]
                    actualizados += 1
                    break

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Proceso finalizado con éxito. Parejas actualizadas: {actualizados}")

if __name__ == "__main__":
    datos = extraer_partidos_con_navegador()
    actualizar_partidak_html(datos)
