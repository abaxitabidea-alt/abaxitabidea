import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URLS_COMPETICION = [
    # Alevín 1º
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3235"
]

CLUB_BUSQUEDA = "ABAXITABIDEA"

def normalizar_texto(texto):
    """Convierte texto a minúsculas y homogeneiza variantes como tx/x y guiones."""
    texto = texto.lower()
    texto = texto.replace("tx", "x").replace("–", "-").replace("—", "-")
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    return texto.strip()

def extraer_partidos_fnpv():
    partidos_encontrados = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for url in URLS_COMPETICION:
            print(f"--> Abriendo ventana en FNPV: {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Esperar 3 segundos adicionales para asegurar carga de JS interno
                page.wait_for_timeout(3000)
                
                # Inspeccionar tanto la página principal como los posibles iframes
                marcos = [page] + page.frames
                
                for marco in marcos:
                    try:
                        filas = marco.query_selector_all("tr")
                        for fila in filas:
                            texto_fila = fila.inner_text().strip()
                            
                            if CLUB_BUSQUEDA in texto_fila.upper():
                                celdas = [c.inner_text().strip() for c in fila.query_selector_all("td, th")]
                                
                                if len(celdas) >= 4:
                                    fecha_hora = celdas[0] if len(celdas) > 0 and celdas[0] else "--"
                                    fronton = celdas[1] if len(celdas) > 1 and celdas[1] else "--"
                                    local = celdas[2] if len(celdas) > 2 else ""
                                    visitante = celdas[4] if len(celdas) > 4 else (celdas[3] if len(celdas) > 3 else "")
                                    
                                    if CLUB_BUSQUEDA in local.upper():
                                        equipo_nuestro = local
                                        rival = visitante
                                    else:
                                        equipo_nuestro = visitante
                                        rival = local
                                    
                                    clave = normalizar_texto(equipo_nuestro)
                                    partidos_encontrados[clave] = {
                                        "aurkaria": rival,
                                        "fronton": fronton,
                                        "horario": fecha_hora
                                    }
                                    print(f"   [ENCONTRADO FNPV]: {equipo_nuestro} vs {rival}")
                    except Exception:
                        continue

            except Exception as e:
                print(f"Error procesando URL {url}: {e}")
                
        browser.close()
        
    return partidos_encontrados

def actualizar_partidak_html(datos_partidos):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print("Error: partidak.html no fue encontrado en la raíz.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    actualizados = 0

    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 4:
            texto_pareja_html = tds[0].get_text(strip=True)
            pareja_norm = normalizar_texto(texto_pareja_html)
            
            # Extraer apellidos o nombres de la pareja del HTML
            componentes = [p.strip() for p in pareja_norm.split('-') if len(p.strip()) >= 3]
            
            for fnpv_clave, datos in datos_partidos.items():
                # Verificar coincidencia si al menos un integrante coincide
                if any(comp in fnpv_clave for comp in componentes):
                    tds[1].string = datos["aurkaria"]
                    tds[2].string = datos["fronton"]
                    tds[3].string = datos["horario"]
                    actualizados += 1
                    print(f"   [ACTUALIZADO EN HTML]: {texto_pareja_html}")
                    break

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"--> Resultado final: {actualizados} filas actualizadas en partidak.html")

if __name__ == "__main__":
    datos = extraer_partidos_fnpv()
    actualizar_partidak_html(datos)
