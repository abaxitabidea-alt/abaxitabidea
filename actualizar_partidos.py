import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URLS_COMPETICION = [
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3235"
]

CLUB_BUSQUEDA = "ABAXITABIDEA"

def parsear_fecha(texto_horario):
    """Extrae la fecha en formato DD/MM/YYYY y devuelve un objeto datetime para comparar."""
    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', texto_horario)
    if match:
        try:
            return datetime.strptime(match.group(1), "%d/%m/%Y")
        except ValueError:
            return None
    return None

def extraer_partidos_fnpv():
    # Estructura: {"pareja_norm": [lista_de_partidos]}
    partidos_encontrados = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for url in URLS_COMPETICION:
            print(f"--> Conectando a FNPV...")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)
                
                marcos = [page] + page.frames
                
                for marco in marcos:
                    try:
                        filas = marco.query_selector_all("tr")
                        for fila in filas:
                            texto_fila = fila.inner_text().strip()
                            
                            if CLUB_BUSQUEDA in texto_fila.upper():
                                celdas = [c.inner_text().strip() for c in fila.query_selector_all("td, th")]
                                
                                if len(celdas) >= 4:
                                    fecha_hora = celdas[0] if celdas[0] else "--"
                                    fronton = celdas[1] if celdas[1] else "--"
                                    local = celdas[2] if len(celdas) > 2 else ""
                                    visitante = celdas[4] if len(celdas) > 4 else (celdas[3] if len(celdas) > 3 else "")
                                    
                                    if CLUB_BUSQUEDA in local.upper():
                                        equipo_nuestro = local
                                        rival = visitante
                                    else:
                                        equipo_nuestro = visitante
                                        rival = local
                                    
                                    clave = " ".join(equipo_nuestro.lower().split())
                                    
                                    if clave not in partidos_encontrados:
                                        partidos_encontrados[clave] = []
                                        
                                    partidos_encontrados[clave].append({
                                        "aurkaria": rival,
                                        "fronton": fronton,
                                        "horario": fecha_hora,
                                        "dt": parsear_fecha(fecha_hora)
                                    })
                    except Exception:
                        continue

            except Exception as e:
                print(f"Error cargando URL {url}: {e}")
                
        browser.close()
        
    # Filtrar para seleccionar el partido MÁS PRÓXIMO (futuro o de hoy)
    partidos_proximos = {}
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for pareja, lista in partidos_encontrados.items():
        # Filtrar partidos que tengan fecha válida y sean hoy o en el futuro
        futuros = [p for p in lista if p["dt"] and p["dt"] >= hoy]
        
        if futuros:
            # Ordenar por fecha más cercana y coger el primero
            futuros.sort(key=lambda x: x["dt"])
            partidos_proximos[pareja] = futuros[0]
        else:
            # Si todos son pasados o no hay fecha clara, coger el último disponible
            partidos_proximos[pareja] = lista[-1]

    return partidos_proximos

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
        if len(tds) >= 4:
            texto_pareja_html = tds[0].get_text(strip=True)
            clave_html = " ".join(texto_pareja_html.lower().split())
            
            if clave_html in datos_partidos:
                datos = datos_partidos[clave_html]
                
                # Escribir rival, frontón y fecha
                tds[1].string = datos["aurkaria"]
                tds[2].string = datos["fronton"]
                tds[3].string = datos["horario"]
                
                # Eliminar la clase CSS que ponía el texto en gris/cursiva
                if 'class' in tds[1].attrs:
                    del tds[1]['class']
                
                actualizados += 1
                print(f"   [ÉXITO PRÓXIMA JORNADA]: '{texto_pareja_html}' -> {datos['aurkaria']} ({datos['horario']})")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"--> Proceso finalizado. Filas actualizadas en partidak.html: {actualizados}")

if __name__ == "__main__":
    partidos = extraer_partidos_fnpv()
    actualizar_partidak_html(partidos)
