import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URLS_COMPETICION = [
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3235"
]

CLUB_BUSQUEDA = "ABAXITABIDEA"

def normalizar(texto):
    """Convierte a minúsculas y elimina acentos/caracteres especiales."""
    texto = texto.lower()
    texto = texto.replace("petrotx", "petrox").replace("tx", "x")
    texto = texto.replace("–", "-").replace("—", "-")
    return re.sub(r'[^a-z0-9\s-]', '', texto).strip()

def extraer_partidos_fnpv():
    partidos_encontrados = []
    
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
                                    
                                    partidos_encontrados.append({
                                        "equipo_raw": equipo_nuestro,
                                        "equipo_norm": normalizar(equipo_nuestro),
                                        "aurkaria": rival,
                                        "fronton": fronton,
                                        "horario": fecha_hora
                                    })
                    except Exception:
                        continue

            except Exception as e:
                print(f"Error cargando URL {url}: {e}")
                
        browser.close()
        
    return partidos_encontrados

def actualizar_partidak_html(lista_partidos):
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
            pareja_html_norm = normalizar(texto_pareja_html)
            
            # Extraer las palabras de más de 3 letras del HTML
            palabras_html = [p for p in re.split(r'[\s\-]+', pareja_html_norm) if len(p) >= 3 and p != "abaxitabidea"]
            
            for partido in lista_partidos:
                # Comprobar si al menos una de las palabras del HTML está en el nombre del partido FNPV
                coincidencia = any(palabra in partido["equipo_norm"] for palabra in palabras_html)
                
                if coincidencia:
                    tds[1].string = partido["aurkaria"]
                    tds[2].string = partido["fronton"]
                    tds[3].string = partido["horario"]
                    actualizados += 1
                    print(f"   [ÉXITO] Matcheado: '{texto_pareja_html}' -> {partido['aurkaria']} | {partido['horario']}")
                    break

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"--> Proceso finalizado. Filas actualizadas en partidak.html: {actualizados}")

if __name__ == "__main__":
    partidos = extraer_partidos_fnpv()
    actualizar_partidak_html(partidos)
