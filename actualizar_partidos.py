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
    partidos_casa = []
    partidos_fuera = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"--> Conectando a la cartelera: {URL_CARTELERA}")
        try:
            page.goto(URL_CARTELERA, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            
            selects = page.query_selector_all("select")

            for sel in selects:
                options = sel.query_selector_all("option")
                for opt in options:
                    texto_opt = normalizar_texto(opt.inner_text())
                    if "JDN" in texto_opt and "36M" in texto_opt:
                        sel.select_option(value=opt.get_attribute("value"))
                        break

            for sel in selects:
                options = sel.query_selector_all("option")
                for opt in options:
                    texto_opt = normalizar_texto(opt.inner_text())
                    if "ABAXITABIDEA" in texto_opt:
                        sel.select_option(value=opt.get_attribute("value"))
                        break

            btn_buscar = page.query_selector("input[value*='BUSCAR'], input[type='submit'], button[type='submit']")
            if btn_buscar:
                btn_buscar.click()
            else:
                page.evaluate("document.forms[0] ? document.forms[0].submit() : null")
                
            page.wait_for_timeout(3000)

            filas = page.query_selector_all("tr")

            for fila in filas:
                texto_fila = normalizar_texto(fila.inner_text())
                celdas = [c.inner_text().strip() for c in fila.query_selector_all("td, th")]
                
                if "ABAXITABIDEA" in texto_fila and len(celdas) >= 6:
                    partido = {
                        "fecha": celdas[0] if celdas[0] else "--",
                        "hora": celdas[1].replace('\n', ' ').strip() if celdas[1] else "--",
                        "num_partida": celdas[2] if celdas[2] else "--",
                        "fronton": celdas[3] if celdas[3] else "--",
                        "local": celdas[4] if celdas[4] else "--",
                        "visitante": celdas[5] if celdas[5] else "--"
                    }
                    
                    # Si se juega en Ororbia es de casa
                    if "ORORBIA" in normalizar_texto(partido["fronton"]):
                        partidos_casa.append(partido)
                    else:
                        partidos_fuera.append(partido)

        except Exception as e:
            print(f"Error cargando la cartelera: {e}")
            
        browser.close()

    # Ordenar partidos de casa por el número de partido
    def obtener_num(p):
        try:
            return int(p["num_partida"])
        except ValueError:
            return 99

    partidos_casa.sort(key=obtener_num)
    
    return partidos_casa, partidos_fuera

def generar_tabla(soup, titulo_seccion, lista_partidos):
    if not lista_partidos:
        return None

    div_seccion = soup.new_tag('div')
    
    h3 = soup.new_tag('h3', **{'class': 'seccion-titulo'})
    h3.string = titulo_seccion
    div_seccion.append(h3)

    table = soup.new_tag('table')
    thead = soup.new_tag('thead')
    tr_head = soup.new_tag('tr')
    
    for h in ["DATA / FECHA", "ORDUTEGIA / HORA", "ZNBK / Nº PARTIDA", "TOKIA / FRONTÓN", "ETXEKOA / LOCAL", "KANPOKOA / VISITANTE"]:
        th = soup.new_tag('th')
        th.string = h
        tr_head.append(th)
    thead.append(tr_head)
    table.append(thead)

    tbody = soup.new_tag('tbody')
    for p in lista_partidos:
        tr = soup.new_tag('tr')
        
        for clave in ["fecha", "hora", "num_partida", "fronton"]:
            td = soup.new_tag('td')
            td.string = p[clave]
            tr.append(td)

        td_local = soup.new_tag('td')
        td_local.string = p["local"]
        if "ABAXITABIDEA" in normalizar_texto(p["local"]):
            td_local['class'] = 'nuestro'
        tr.append(td_local)

        td_vis = soup.new_tag('td')
        td_vis.string = p["visitante"]
        if "ABAXITABIDEA" in normalizar_texto(p["visitante"]):
            td_vis['class'] = 'nuestro'
        tr.append(td_vis)

        tbody.append(tr)

    table.append(tbody)
    div_seccion.append(table)
    return div_seccion

def actualizar_partidak_html(partidos_casa, partidos_fuera):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    contenedor = soup.find('div', id='partidos-contenedor')
    if not contenedor:
        return

    contenedor.clear()

    tabla_casa = generar_tabla(soup, "ETXEAN / ETXEKO PARTIDAK (CASA)", partidos_casa)
    if tabla_casa:
        contenedor.append(tabla_casa)

    tabla_fuera = generar_tabla(soup, "KANPOAN / KANPOKO PARTIDAK (FUERA)", partidos_fuera)
    if tabla_fuera:
        contenedor.append(tabla_fuera)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print("--> `partidak.html` actualizado correctamente sin categorías y ordenado por casa/fuera.")

if __name__ == "__main__":
    casa, fuera = extraer_partidos_cartelera()
    actualizar_partidak_html(casa, fuera)
