import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URLS_COMPETICION = [
    # Alevín 1º (URL directa a la tabla de partidos)
    "https://www.fnpelota.com/pub/ModalidadComp.asp?idioma=ca&idCompeticion=3235"
]

CLUB_BUSQUEDA = "ABAXITABIDEA"

def normalizar(texto):
    """Limpia tildes, signos y normaliza variantes como tx / x"""
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
            print(f"Navegando a: {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Si existe un iframe con las clasificaciones/partidos, cambiar al iframe
                frame_target = page
                for frame in page.frames:
                    if "Modalidad" in frame.url or "competicion" in frame.url.lower():
                        frame_target = frame
                        break
                
                # Esperar a que se rendericen las tablas
                frame_target.wait_for_selector("table", timeout=15000)
                
                html_contenido = frame_target.content()
                soup = BeautifulSoup(html_contenido, 'html.parser')
                
                for tabla in soup.find_all('table'):
                    for fila in tabla.find_all('tr'):
                        celdas = [c.get_text(strip=True) for c in fila.find_all(['td', 'th'])]
                        
                        if len(celdas) >= 4:
                            texto_fila = " ".join(celdas).upper()
                            
                            if CLUB_BUSQUEDA in texto_fila:
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
                                
                                key = normalizar(equipo_nuestro)
                                partidos_encontrados[key] = {
                                    "aurkaria": rival,
                                    "fronton": fronton,
                                    "horario": fecha_hora
                                }
                                print(f"-> Detectado en FNPV: {equipo_nuestro} vs {rival}")
                                
            except Exception as e:
                print(f"Error cargando URL {url}: {e}")
                
        browser.close()
        
    return partidos_encontrados

def actualizar_partidak_html(datos_partidos):
    file_path = "partidak.html"
    if not os.path.exists(file_path):
        print("Error: partidak.html no existe.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    actualizados = 0

    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 4:
            texto_pareja_html = tds[0].get_text(strip=True)
            pareja_norm = normalizar(texto_pareja_html)
            
            # Obtener fragmentos/apellidos principales (mínimo 3 letras)
            apellidos = [p.strip() for p in pareja_norm.split('-') if len(p.strip()) >= 3]
            
            for fnpv_key, datos in datos_partidos.items():
                # Verificar coincidencia por apellido/nombre de cualquier integrante
                coincide = any(apellido in fnpv_key for apellido in apellidos)
                
                if coincide:
                    tds[1].string = datos["aurkaria"]
                    tds[2].string = datos["fronton"]
                    tds[3].string = datos["horario"]
                    actualizados += 1
                    print(f"-> Actualizado HTML: {texto_pareja_html} -> {datos['aurkaria']}")
                    break

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Proceso finalizado. Filas actualizadas en HTML: {actualizados}")

if __name__ == "__main__":
    datos = extraer_partidos_fnpv()
    actualizar_partidak_html(datos)
