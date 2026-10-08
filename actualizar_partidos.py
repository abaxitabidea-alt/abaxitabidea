import os
import re
import unicodedata
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_CARTELERA = "https://www.fnpelota.com/pub/cartelera.asp?idioma=ca"

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
            page.wait_for_timeout(2000)
            
            selects = page.query_selector_all("select")

            # 1. Seleccionar COMPETICIÓN (JDN 36M MANO)
            for sel in selects:
                options = sel.query_selector_all("option")
                for opt in options:
                    texto_opt = normalizar_texto(opt.inner_text())
                    if "JDN" in texto_opt and "36M" in texto_opt:
                        sel.select_option(value=opt.get_attribute("value"))
                        break

            # 2. Seleccionar CLUB (C.P. ABAXITABIDEA TALDE)
            for sel in selects:
                options = sel.query_selector_all("option")
                for opt in options:
                    texto_opt = normalizar_texto(opt.inner_text())
                    if "ABAXITABIDEA" in texto_opt:
                        sel.select_option(value=opt.get_attribute("value"))
                        break

            # 3. Hacer clic en BUSCAR
            btn_buscar = page.query_selector("input[value*='BUSCAR'], input[type='submit'], button[type='submit']")
            if btn_buscar:
                btn_buscar.click()
            else:
                page.evaluate("document.forms[0] ? document.forms[0].submit() : null")
                
            page.wait_for_timeout(3000)

            # Extraer filas
            filas = page.query_selector_all("tr")

            for fila in filas:
                texto_fila = normalizar_texto(fila.inner_text())
                celdas = [c.inner_text().strip() for c in fila.query_selector_all("td, th")]
                
                if "ABAXITABIDEA" in texto_fila and len(celdas) >= 6:
                    partidos_encontrados.append({
                        "fecha": celdas[0] if celdas[0] else "--",
                        "hora": celdas[1].replace('\n', ' ').strip() if celdas[1] else "--",
                        "num_partida": celdas[2] if celdas[2] else "--",
                        "fronton": celdas[3] if celdas[3] else "--",
                        "local": celdas[4] if celdas[4] else "--",
                        "visitante": celdas[5] if celdas[5] else "--"
                    })
        except Exception as e:
            print(f"Error cargando la cartelera: {e}")
            
        browser.close()
        
    print(f"--> Partidos detectados: {len(partidos_encontrados)}")
    return partidos_encontrados

def actualizar_partidak_html(partidos_web):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print("Error: no existe partidak.html")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    idx_partido = 0
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) == 6:
            if idx_partido < len(partidos_web):
                partido = partidos_web[idx_partido]
                tds[0].string = partido["fecha"]
                tds[1].string = partido["hora"]
                tds[2].string = partido["num_partida"]
                tds[3].string = partido["fronton"]
                tds[4].string = partido["local"]
                tds[5].string = partido["visitante"]

                if "ABAXITABIDEA" in normalizar_texto(partido["local"]):
                    tds[4]['class'] = 'nuestro'
                    if 'class' in tds[5].attrs: del tds[5]['class']
                else:
                    tds[5]['class'] = 'nuestro'
                    if 'class' in tds[4].attrs: del tds[4]['class']
                idx_partido += 1
            else:
                tds[0].string = "--"
                tds[1].string = "--"
                tds[2].string = "--"
                tds[3].string = "--"
                tds[5].string = "Atsedena / Descanso"
                tds[5]['class'] = 'descanso'

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print("--> `partidak.html` actualizado con éxito.")

if __name__ == "__main__":
    partidos = extraer_partidos_cartelera()
    actualizar_partidak_html(partidos)
