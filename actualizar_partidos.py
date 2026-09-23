import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URLS = [
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3235",
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3233",
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3232",
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3237&temp=2026",
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3240&temp=2026",
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3241&temp=2026",
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3239&temp=2026"
]

HTML_FILE = "partidak.html"

def normalizar_texto(texto):
    if not texto:
        return ""
    return re.sub(r'\s+', ' ', texto).strip()

def extraer_datos_fnpv():
    partidos_encontrados = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for url in URLS:
            try:
                print(f"--> Conectando a FNPV: {url}")
                page.goto(url, wait_until="networkidle", timeout=30000)
                soup = BeautifulSoup(page.content(), "html.parser")

                tablas = soup.find_all("table")
                for tabla in tablas:
                    filas = tabla.find_all("tr")
                    jornada_actual = None

                    for fila in filas:
                        texto_fila = normalizar_texto(fila.text)
                        
                        if "Jornada 1" in texto_fila:
                            jornada_actual = 1
                        elif "Jornada 2" in texto_fila and jornada_actual == 1:
                            break

                        celdas = fila.find_all(["td", "th"])
                        if len(celdas) >= 4 and jornada_actual == 1:
                            fecha_hora = normalizar_texto(celdas[0].text)
                            fronton = normalizar_texto(celdas[1].text)
                            local = normalizar_texto(celdas[2].text)
                            visitante = normalizar_texto(celdas[4].text) if len(celdas) > 4 else normalizar_texto(celdas[3].text)

                            partes_fecha = fecha_hora.split()
                            fecha = partes_fecha[0] if len(partes_fecha) > 0 else "-"
                            hora = partes_fecha[1] if len(partes_fecha) > 1 else "-"

                            if "ABAXITABIDEA" in local.upper():
                                partidos_encontrados[local] = {
                                    "rival": visitante,
                                    "fronton": fronton if fronton and fronton != "-" else "-",
                                    "fecha": fecha,
                                    "hora": hora
                                }
                            elif "ABAXITABIDEA" in visitante.upper():
                                partidos_encontrados[visitante] = {
                                    "rival": local,
                                    "fronton": fronton if fronton and fronton != "-" else "-",
                                    "fecha": fecha,
                                    "hora": hora
                                }

            except Exception as e:
                print(f"Error procesando {url}: {e}")

        browser.close()

    return partidos_encontrados

def actualizar_partidak_html(partidos_fnpv):
    if not os.path.exists(HTML_FILE):
        print(f"Error: No se encontró el archivo {HTML_FILE}")
        return

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    filas_actualizadas = 0

    tablas = soup.find_all("table")
    for tabla in tablas:
        filas = tabla.find_all("tr")
        for fila in filas:
            celdas = fila.find_all("td")
            if len(celdas) >= 4:
                pareja_nuestra = normalizar_texto(celdas[0].text)

                if pareja_nuestra in partidos_fnpv:
                    info = partidos_fnpv[pareja_nuestra]
                    rival = info["rival"]

                    if rival.lower() in ["descanso", "atsegina"]:
                        celdas[1].string = "Descanso"
                        celdas[2].string = "--"
                        celdas[3].string = "--"
                        print(f"[DESCANSO DETECTADO]: '{pareja_nuestra}' -> Descanso")
                    else:
                        celdas[1].string = rival
                        celdas[2].string = info["fronton"]
                        
                        if info["hora"] != "-":
                            celdas[3].string = f"{info['fecha']} - {info['hora']}"
                        else:
                            celdas[3].string = f"{info['fecha']} -"
                        
                        print(f"[ÉXITO PRÓXIMA JORNADA]: '{pareja_nuestra}' -> {rival} ({celdas[3].string})")

                    filas_actualizadas += 1

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"\n--> Proceso finalizado. Filas actualizadas en {HTML_FILE}: {filas_actualizadas}")

if __name__ == "__main__":
    datos = extraer_datos_fnpv()
    actualizar_partidak_html(datos)
