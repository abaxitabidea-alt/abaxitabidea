import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_CARTELERA = "https://www.fnpelota.com/pub/cartelera.asp?idioma=ca&selSemana=&selClub=&selCompeticion=&excel=0"
CLUB_BUSQUEDA = "ABAXITABIDEA"

def extraer_partidos_cartelera():
    partidos_encontrados = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"--> Conectando a la cartelera: {URL_CARTELERA}")
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
                            
                            if len(celdas) >= 6:
                                fecha = celdas[0] if celdas[0] else "--"
                                hora = celdas[1] if celdas[1] else "--"
                                num_partida = celdas[2] if celdas[2] else "--"
                                fronton = celdas[3] if celdas[3] else "--"
                                equipo_local = celdas[4] if celdas[4] else "--"
                                equipo_visitante = celdas[5] if celdas[5] else "--"
                                
                                # Guardar la partida para la pareja correspondiente
                                datos_partido = {
                                    "fecha": fecha,
                                    "hora": hora,
                                    "num_partida": num_partida,
                                    "fronton": fronton,
                                    "local": equipo_local,
                                    "visitante": equipo_visitante
                                }
                                
                                # Indexamos por los textos de ambos equipos
                                clave = f"{equipo_local.lower()} {equipo_visitante.lower()}"
                                partidos_encontrados[clave] = datos_partido
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
        # Verificar que es una fila de tabla con 6 columnas
        if len(tds) == 6:
            texto_local = tds[4].get_text(strip=True)
            texto_visitante = tds[5].get_text(strip=True)
            
            # Extraer apellidos principales de nuestra pareja en la celda HTML
            apellidos = [p.lower() for p in (texto_local + " " + texto_visitante).split() if len(p) > 3 and p.lower() not in ["abaxitabidea", "atsedena", "descanso", "--"]]
            
            coincidencia = None
            for clave_partido, partido in datos_partidos.items():
                if apellidos and all(ap in clave_partido for ap in apellidos):
                    coincidencia = partido
                    break

            if coincidencia:
                tds[0].string = coincidencia["fecha"]
                tds[1].string = coincidencia["hora"]
                tds[2].string = coincidencia["num_partida"]
                tds[3].string = coincidencia["fronton"]
                tds[4].string = coincidencia["local"]
                tds[5].string = coincidencia["visitante"]
                
                if CLUB_BUSQUEDA in coincidencia["local"].upper():
                    tds[4]['class'] = 'nuestro'
                    if 'class' in tds[5].attrs: del tds[5]['class']
                else:
                    tds[5]['class'] = 'nuestro'
                    if 'class' in tds[4].attrs: del tds[4]['class']
                
                actualizados += 1
                print(f"   [ENCONTRADO]: {coincidencia['local']} vs {coincidencia['visitante']}")
            else:
                # Si no aparece en la cartelera de la semana, se marca descanso
                tds[0].string = "--"
                tds[1].string = "--"
                tds[2].string = "--"
                tds[3].string = "--"
                tds[5].string = "Atsedena / Descanso"
                tds[5]['class'] = 'descanso'

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"\n--> Proceso finalizado. Filas actualizadas: {actualizados}")

if __name__ == "__main__":
    partidos = extraer_partidos_cartelera()
    actualizar_partidak_html(partidos)
