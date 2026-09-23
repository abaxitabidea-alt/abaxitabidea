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

def limpiar_texto(texto):
    if not texto:
        return ""
    return re.sub(r'\s+', ' ', texto).strip()

def extraer_clave_pareja(texto):
    """Extrae los nombres dentro de paréntesis para hacer un match flexible."""
    match = re.search(r'\((.*?)\)', texto)
    if match:
        nombres = match.group(1).lower()
        # Ordenamos los nombres de los pelotaris para dar igual el orden
        partes = sorted([p.strip() for p in re.split(r'[-–/]', nombres)])
        return "-".join(partes)
    return limpiar_texto(texto).lower()

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
                        texto_fila = limpiar_texto(fila.text)
                        
                        if "Jornada 1" in texto_fila:
                            jornada_actual = 1
                        elif "Jornada 2" in texto_fila and jornada_actual == 1:
                            break

                        celdas = [limpiar_texto(c.text) for c in fila.find_all(["td", "th"])]
                        
                        if jornada_actual == 1 and len(celdas) >= 3:
                            fecha_hora = celdas[0] if len(celdas) > 0 else "-"
                            fronton = celdas[1] if len(celdas) > 1 else "-"
                            local = celdas[2] if len(celdas) > 2 else ""
                            visitante = celdas[-1] if len(celdas) >= 4 else ""

                            # Extraer fecha
                            partes_fecha = fecha_hora.split()
                            fecha = partes_fecha[0] if partes_fecha else "-"
                            hora = partes_fecha[1] if len(partes_fecha) > 1 else "-"

                            # Evaluar si juega ABAXITABIDEA
                            for eq_guerra, eq_rival in [(local, visitante), (visitante, local)]:
                                if "ABAXITABIDEA" in eq_guerra.upper():
                                    clave = extraer_clave_pareja(eq_guerra)
                                    partidos_encontrados[clave] = {
                                        "nombre_original": eq_guerra,
                                        "rival": eq_rival if eq_rival else "Descanso",
                                        "fronton": fronton if fronton != "-" else "--",
                                        "fecha": fecha,
                                        "hora": hora
                                    }

            except Exception as e:
                print(f"Error procesando {url}: {e}")

        browser.close()

    return partidos_encontrados

def actualizar_partidak_html(partidos_fnpv):
    if not os.path.exists(HTML_FILE):
        print(f"Error: No se encontró {HTML_FILE}")
        return

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    filas_actualizadas = 0

    for tabla in soup.find_all("table"):
        for fila in tabla.find_all("tr"):
            celdas = fila.find_all("td")
            if len(celdas) >= 4:
                pareja_html = limpiar_texto(celdas[0].text)
                clave_html = extraer_clave_pareja(pareja_html)

                if clave_html in partidos_fnpv:
                    info = partidos_fnpv[clave_html]
                    rival = info["rival"]

                    if rival.lower() in ["descanso", "atsegina", ""]:
                        celdas[1].string = "Descanso"
                        celdas[2].string = "--"
                        celdas[3].string = "--"
                        print(f"[DESCANSO]: '{pareja_html}' -> Descanso")
                    else:
                        celdas[1].string = rival
                        celdas[2].string = info["fronton"]
                        if info["hora"] != "-":
                            celdas[3].string = f"{info['fecha']} - {info['hora']}"
                        else:
                            celdas[3].string = f"{info['fecha']} -"
                        print(f"[ÉXITO]: '{pareja_html}' -> {rival} ({celdas[3].string})")

                    filas_actualizadas += 1

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"\n--> Proceso finalizado. Filas actualizadas en {HTML_FILE}: {filas_actualizadas}")

if __name__ == "__main__":
    datos = extraer_datos_fnpv()
    actualizar_partidak_html(datos)
