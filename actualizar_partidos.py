import os
import requests
from bs4 import BeautifulSoup

# URL de Competición FNPV (Juvenil 1ª)
URL_FNPV = "https://www.fnpelota.com/pub/modalidadescompeticion.asp?idioma=ca&idCategoria=3204&temp=2026"

def buscar_partido_irurtzun():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    # Pareja de prueba / simulacro exacta
    club = "IRURTZUN"
    jugadores = "E. Esain - P. Gorraiz"
    
    print(f"Buscando señalamiento para {club} ({jugadores})...")
    
    try:
        response = requests.get(URL_FNPV, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"Error al acceder a la FNPV (Status Code: {response.status_code})")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar en todas las tablas de la página web de la FNPV
        tablas = soup.find_all('table')
        partido_datos = None
        
        for tabla in tablas:
            texto_tabla = tabla.get_text()
            if "irurtzun" in texto_tabla.lower() or "esain" in texto_tabla.lower():
                filas = tabla.find_all('tr')
                for fila in filas:
                    celdas = [c.get_text(strip=True) for c in fila.find_all(['td', 'th'])]
                    texto_fila = " ".join(celdas).lower()
                    if "irurtzun" in texto_fila or "esain" in texto_fila:
                        print(f"¡Fila encontrada!: {celdas}")
                        partido_datos = celdas
                        break

        if not partido_datos:
            print("No se encontró la pareja directamente en el HTML base. Revisando enlaces/PDFs adjuntos...")
            
        return partido_datos

    except Exception as e:
        print(f"Error durante el scraping: {e}")
        return None

def actualizar_partidak_html(datos_partido):
    if not os.path.exists("partidak.html"):
        print("Error: partidak.html no existe.")
        return

    print("Comprobación de actualización sobre partidak.html completada.")

if __name__ == "__main__":
    partido = buscar_partido_irurtzun()
    actualizar_partidak_html(partido)
