import os
import re
import unicodedata
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_CARTELERA = "https://www.fnpelota.com/pub/cartelera.asp?idioma=ca"

def normalizar_texto(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = re.sub(r'[\u0300-\u036f]', '', texto)
    return texto.upper().strip()

def extraer_partidos_cartelera():
    partidos_por_categoria = {}
    
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

            # 3. Buscar
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
                    # Extraer la categoría desde la última celda si existe
                    categoria = "PARTIDOS"
                    if len(celdas) >= 7:
                        raw_cat = celdas[6].replace('\n', ' ').strip()
                        # Extraer solo la parte relevante (ej. BENJAMIN 3ª LIGA -> Benjamín 3º)
                        match = re.search(r'(BENJAMIN|ALEVIN|INFANTIL|CADETE|JUVENIL|SENIOR)\s*(\d+)?', normalizar_texto(raw_cat))
                        if match:
                            cat_nombre = match.group(1).capitalize()
                            cat_num = match.group(2) + "º" if match.group(2) else ""
                            categoria = f"{cat_nombre} {cat_num}".strip()
                        else:
                            categoria = raw_cat

                    partido = {
                        "fecha": celdas[0] if celdas[0] else "--",
                        "hora": celdas[1].replace('\n', ' ').strip() if celdas[1] else "--",
                        "num_partida": celdas[2] if celdas[2] else "--",
                        "fronton": celdas[3] if celdas[3] else "--",
                        "local": celdas[4] if celdas[4] else "--",
                        "visitante": celdas[5] if celdas[5] else "--"
                    }

                    if categoria not in partidos_por_categoria:
                        partidos_por_categoria[categoria] = []
                    partidos_por_categoria[categoria].append(partido)

        except Exception as e:
            print(f"Error cargando la cartelera: {e}")
            
        browser.close()
        
    return partidos_por_categoria

def actualizar_partidak_html(partidos_dict):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print("Error: no existe partidak.html")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    container = soup.find('div', class_='container')
    if not container:
        print("Error: No se encontró .container en partidak.html")
        return

    # Eliminar bloques de tablas anteriores
    for bloque in container.find_all('div', class_='categoria-block'):
        bloque.decompose()

    if not partidos_dict:
        print("No se encontraron partidos para actualizar.")
        return

    # Generar bloques por cada categoría real
    for cat_titulo, partidos in partidos_dict.items():
        bloque = soup.new_tag('div', **{'class': 'categoria-block'})
        
        # Header de la categoría
        header_div = soup.new_tag('div', **{'class': 'categoria-header'})
        h3 = soup.new_tag('h3')
        h3.string = cat_titulo
        header_div.append(h3)
        bloque.append(header_div)

        # Tabla
        table = soup.new_tag('table', **{'class': 'tabla-partidos'})
        thead = soup.new_tag('thead')
        tr_head = soup.new_tag('tr')
        
        headers = ["DATA / FECHA", "ORDUTEGIA / HORA", "ZNBK / Nº PARTIDA", "TOKIA / FRONTÓN", "ETXEKOA / LOCAL", "KANPOKOA / VISITANTE"]
        for h in headers:
            th = soup.new_tag('th')
            th.string = h
            tr_head.append(th)
        thead.append(tr_head)
        table.append(thead)

        tbody = soup.new_tag('tbody')
        for p in partidos:
            tr = soup.new_tag('tr')
            
            td_fecha = soup.new_tag('td')
            td_fecha.string = p["fecha"]
            tr.append(td_fecha)

            td_hora = soup.new_tag('td')
            td_hora.string = p["hora"]
            tr.append(td_hora)

            td_num = soup.new_tag('td')
            td_num.string = p["num_partida"]
            tr.append(td_num)

            td_fronton = soup.new_tag('td')
            td_fronton.string = p["fronton"]
            tr.append(td_fronton)

            td_local = soup.new_tag('td')
            td_local.string = p["local"]
            if "ABAXITABIDEA" in normalizar_texto(p["local"]):
                td_local['class'] = 'nuestro'
            tr.append(td_local)

            td_visitante = soup.new_tag('td')
            td_visitante.string = p["visitante"]
            if "ABAXITABIDEA" in normalizar_texto(p["visitante"]):
                td_visitante['class'] = 'nuestro'
            tr.append(td_visitante)

            tbody.append(tr)

        table.append(tbody)
        bloque.append(table)
        container.append(bloque)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print("--> `partidak.html` reestructurado y actualizado con éxito por categorías reales.")

if __name__ == "__main__":
    partidos_dict = extraer_partidos_cartelera()
    actualizar_partidak_html(partidos_dict)
