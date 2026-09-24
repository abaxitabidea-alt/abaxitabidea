import os
import re
import unicodedata
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# URL filtrando directamente por el club ABAXITABIDEA
URL_CARTELERA = "https://www.fnpelota.com/pub/cartelera.asp?idioma=ca&selSemana=&selClub=ABAXITABIDEA&selCompeticion=&excel=0"
CLUB_BUSQUEDA = "ABAXITABIDEA"

def normalizar_texto(texto):
    """Elimina tildes y convierte a mayúsculas para comparar fácilmente"""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = re.sub(r'[\u0300-\u036f]', '', texto)
    return texto.upper().strip()

def extraer_partidos_cartelera():
    partidos_encontrados = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"--> Conectando a la cartelera: {URL_CARTELERA}")
        try:
            page.goto(URL_CARTELERA, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Buscar en el marco principal y sub-frames
            marcos = [page] + page.frames
            for marco in marcos:
                try:
                    filas = marco.query_selector_all("tr")
                    for fila in filas:
                        texto_fila = normalizar_texto(fila.inner_text())
                        if CLUB_BUSQUEDA in texto_fila:
                            celdas = [c.inner_text().strip() for c in fila.query_selector_all("td, th")]
                            
                            if len(celdas) >= 6:
                                fecha = celdas[0] if celdas[0] else "--"
                                hora = celdas[1] if celdas[1] else "--"
                                num_partida = celdas[2] if celdas[2] else "--"
                                fronton = celdas[3] if celdas[3] else "--"
                                equipo_local = celdas[4] if celdas[4] else "--"
                                equipo_visitante = celdas[5] if celdas[5] else "--"
                                
                                partidos_encontrados.append({
                                    "fecha": fecha,
                                    "hora": hora,
                                    "num_partida": num_partida,
                                    "fronton": fronton,
                                    "local": equipo_local,
                                    "visitante": equipo_visitante,
                                    "texto_normalizado": normalizar_texto(f"{equipo_local} {equipo_visitante}")
                                })
                except Exception:
                    continue
        except Exception as e:
            print(f"Error cargando la cartelera: {e}")
            
        browser.close()
        
    print(f"--> Partidos detectados en la web de la Federación: {len(partidos_encontrados)}")
    return partidos_encontrados

def actualizar_partidak_html(partidos_web):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print("Error: no existe partidak.html")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    actualizados = 0

    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) == 6:
            texto_local = tds[4].get_text(strip=True)
            texto_visitante = tds[5].get_text(strip=True)
            texto_fila_html = normalizar_texto(texto_local + " " + texto_visitante)
            
            # Extraer apellidos clave de nuestra pareja en el HTML
            palabras_clave = [p for p in re.findall(r'\b[A-Z]{3,}\b', texto_fila_html) 
                              if p not in ["ABAXITABIDEA", "ATSEDENA", "DESCANSO", "ZEHAZTEKE"]]
            
            coincidencia = None
            if palabras_clave:
                for partido in partidos_web:
                    # Comprobamos si los apellidos de nuestra pareja están en el partido encontrado
                    if all(apellido in partido["texto_normalizado"] for apellido in palabras_clave):
                        coincidencia = partido
                        break

            if coincidencia:
                tds[0].string = coincidencia["fecha"]
                tds[1].string = coincidencia["hora"]
                tds[2].string = coincidencia["num_partida"]
                tds[3].string = coincidencia["fronton"]
                tds[4].string = coincidencia["local"]
                tds[5].string = coincidencia["visitante"]
                
                # Resaltar si somos Local o Visitante
                if CLUB_BUSQUEDA in normalizar_texto(coincidencia["local"]):
                    tds[4]['class'] = 'nuestro'
                    if 'class' in tds[5].attrs: del tds[5]['class']
                else:
                    tds[5]['class'] = 'nuestro'
                    if 'class' in tds[4].attrs: del tds[4]['class']
                
                actualizados += 1
                print(f"   [ENCONTRADO]: {coincidencia['local']} vs {coincidencia['visitante']}")
            else:
                # Si no aparece en la cartelera semanal, se asigna descanso
                tds[0].string = "--"
                tds[1].string = "--"
                tds[2].string = "--"
                tds[3].string = "--"
                tds[5].string = "Atsedena / Descanso"
                tds[5]['class'] = 'descanso'

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"\n--> Proceso finalizado. Filas actualizadas en HTML: {actualizados}")

if __name__ == "__main__":
    partidos = extraer_partidos_cartelera()
    actualizar_partidak_html(partidos)
