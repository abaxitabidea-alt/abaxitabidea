import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_CARTELERA = "https://www.fnpelota.com/pub/cartelera.asp?idioma=ca&selSemana=&selClub=&selCompeticion=&excel=0"
CLUB_BUSQUEDA = "ABAXITABIDEA"

def extraer_partidos_cartelera():
    partidos_encontrados = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"--> Conectando a la cartelera general: {URL_CARTELERA}")
        try:
            page.goto(URL_CARTELERA, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            
            marcos = [page] + page.frames
            for marco in marcos:
                try:
                    filas = marco.query_selector_all("tr")
                    for fila in filas:
                        texto_fila = fila.inner_text().strip()
                        if CLUB_BUSQUEDA in texto_fila.upper():
                            celdas = [c.inner_text().strip() for c in fila.query_selector_all("td, th")]
                            
                            # Estructura típica de cartelera:
                            # [Fecha, Hora, Nº/Orden, Frontón, Local, Visitante, ...]
                            if len(celdas) >= 6:
                                fecha = celdas[0] if celdas[0] else "--"
                                hora = celdas[1] if celdas[1] else "--"
                                num_partida = celdas[2] if celdas[2] else "--"
                                fronton = celdas[3] if celdas[3] else "--"
                                equipo_local = celdas[4] if celdas[4] else "--"
                                equipo_visitante = celdas[5] if celdas[5] else "--"
                                
                                # Determinamos cuál es nuestra pareja para usar como clave
                                if CLUB_BUSQUEDA in equipo_local.upper():
                                    clave = " ".join(equipo_local.lower().split())
                                else:
                                    clave = " ".join(equipo_visitante.lower().split())
                                
                                if clave not in partidos_encontrados:
                                    partidos_encontrados[clave] = []
                                    
                                partidos_encontrados[clave].append({
                                    "fecha": fecha,
                                    "hora": hora,
                                    "num_partida": num_partida,
                                    "fronton": fronton,
                                    "local": equipo_local,
                                    "visitante": equipo_visitante
                                })
                except Exception:
                    continue
        except Exception as e:
            print(f"Error cargando la cartelera: {e}")
            
        browser.close()
        
    return partidos_encontrados

def actualizar_partidak_html(datos_partidos):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print("Error: no existe partidak.html")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    actualizados = 0

    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        # La tabla nueva tiene 6 columnas: Fecha, Hora, Nº, Frontón, Local, Visitante
        if len(tds) == 6:
            texto_local = tds[4].get_text(strip=True)
            texto_visitante = tds[5].get_text(strip=True)
            texto_referencia = texto_local + " " + texto_visitante
            
            clave_html = " ".join(texto_referencia.lower().split())
            
            coincidencia = None
            if clave_html in datos_partidos:
                coincidencia = datos_partidos[clave_html]
            else:
                for k, v in datos_partidos.items():
                    # Coincidencia por apellidos contenidos en la celda
                    apellidos = [palabra for palabra in clave_html.split() if len(palabra) > 3 and palabra not in ["abaxitabidea", "zehazteke"]]
                    if apellidos and all(ap in k for ap in apellidos):
                        coincidencia = v[0] if isinstance(v, list) else v
                        break

            if coincidencia:
                tds[0].string = coincidencia["fecha"]
                tds[1].string = coincidencia["hora"]
                tds[2].string = coincidencia["num_partida"]
                tds[3].string = coincidencia["fronton"]
                tds[4].string = coincidencia["local"]
                tds[5].string = coincidencia["visitante"]
                
                # Resaltar la posición de Abaxitabidea (negrita en su columna correspondiente)
                if CLUB_BUSQUEDA in coincidencia["local"].upper():
                    tds[4]['class'] = 'nuestro'
                    if 'class' in tds[5].attrs: del tds[5]['class']
                else:
                    tds[5]['class'] = 'nuestro'
                    if 'class' in tds[4].attrs: del tds[4]['class']
                
                actualizados += 1
                print(f"   [ACTUALIZADO]: Partida #{coincidencia['num_partida']} | {coincidencia['local']} vs {coincidencia['visitante']}")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"\n--> Proceso finalizado. Filas actualizadas en partidak.html: {actualizados}")

if __name__ == "__main__":
    partidos = extraer_partidos_cartelera()
    actualizar_partidak_html(partidos)
