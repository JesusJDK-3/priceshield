import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor
import json

# Configuración de headers para emular navegador
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# APIs VTEX (supermercados que usan API REST)
SUPERMERCADOS_API = {
    "plazavea": "https://www.plazavea.com.pe/api/catalog_system/pub/products/search",
    "wong": "https://www.wong.pe/api/catalog_system/pub/products/search",
    "vivanda": "https://www.vivanda.com.pe/api/catalog_system/pub/products/search",
    "metro": "https://www.metro.pe/api/catalog_system/pub/products/search"
}

# Supermercados que requieren scraping con Playwright
SUPERMERCADOS_SCRAPING = ["tottus", "makro"]

# URLs dinámicas para scraping (se formatea con el término de búsqueda)
SCRAPING_URLS = {
    "tottus": "https://tottus.falabella.com.pe/tottus-pe/search?Ntt={}",
    "makro": "https://www.makro.plazavea.com.pe/search/?_query={}"
}


def scrap_supermercado_api(nombre_super, termino_busqueda, limite=10):
    """
    Consulta APIs VTEX de supermercados (PlazaVea, Wong, Vivanda, Metro)
    
    Args:
        nombre_super (str): Nombre del supermercado
        termino_busqueda (str): Producto a buscar (requerido)
        limite (int): Máximo número de productos a retornar
    
    Returns:
        list: Lista de productos con estructura estándar
    """
    if nombre_super not in SUPERMERCADOS_API:
        return []
    
    url = SUPERMERCADOS_API[nombre_super]
    productos = []
    
    try:
        response = requests.get(
            f"{url}?q={termino_busqueda}", 
            headers=HEADERS, 
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        for item in data[:limite]:
            try:
                # Extraer información del producto
                nombre = item.get('productName', 'Sin nombre')
                precio_data = item['items'][0]['sellers'][0]['commertialOffer']
                precio = precio_data.get('Price', 0)
                cantidad_disponible = precio_data.get('AvailableQuantity', 0)
                
                producto = {
                    "nombre": nombre,
                    "precio": float(precio),
                    "disponible": cantidad_disponible > 0,
                    "supermercado": nombre_super.capitalize(),
                    "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "url": item.get('link', ''),
                    "imagen": item.get('items', [{}])[0].get('images', [{}])[0].get('imageUrl', '') if item.get('items') else ''
                }
                productos.append(producto)
                
            except (KeyError, IndexError, TypeError, ValueError) as e:
                continue
        
        print(f"✓ API {nombre_super}: {len(productos)} productos obtenidos")
        return productos
        
    except requests.RequestException as e:
        print(f"❌ Error en API {nombre_super}: {e}")
        return []
    except Exception as e:
        print(f"❌ Error inesperado en {nombre_super}: {e}")
        return []


def scrap_playwright_generico(nombre_super, termino_busqueda, limite=10):
    """
    Scraping genérico con Playwright para supermercados que no tienen API
    
    Args:
        nombre_super (str): Nombre del supermercado (tottus o makro)
        termino_busqueda (str): Producto a buscar (requerido)
        limite (int): Máximo número de productos a extraer
    
    Returns:
        list: Lista de productos con estructura estándar
    """
    if nombre_super not in SCRAPING_URLS:
        return []
    
    productos = []
    url = SCRAPING_URLS[nombre_super].format(termino_busqueda)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage', 
                '--disable-images',
                '--disable-javascript',
                '--disable-plugins',
                '--disable-extensions'
            ]
        )
        
        try:
            page = browser.new_page()
            
            # Optimizaciones de velocidad - bloquear recursos innecesarios
            page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,mp4,mp3}", 
                      lambda route: route.abort())
            page.set_extra_http_headers(HEADERS)
            
            # Navegar a la página
            page.goto(url, timeout=30000, wait_until='domcontentloaded')
            
            if nombre_super == "tottus":
                productos = _extraer_productos_tottus(page, limite)
            elif nombre_super == "makro":
                productos = _extraer_productos_makro(page, limite)
            
            print(f"✓ Scraping {nombre_super}: {len(productos)} productos obtenidos")
            
        except Exception as e:
            print(f"❌ Error en scraping {nombre_super}: {e}")
        finally:
            browser.close()
    
    return productos


def _extraer_productos_tottus(page, limite):
    """Extrae productos específicamente de Tottus"""
    productos = []
    
    try:
        # Scroll para cargar productos dinámicamente
        for i in range(3):
            page.mouse.wheel(0, 800)
            page.wait_for_timeout(500)
        
        # Esperar a que aparezcan los productos
        page.wait_for_selector('b.pod-subTitle', timeout=15000)
        
        # Extraer datos usando JavaScript para mayor eficiencia
        productos_data = page.evaluate(f'''
            () => {{
                const productos = [];
                const nombres = document.querySelectorAll('b.pod-subTitle');
                const precios = document.querySelectorAll('li[data-internet-price]');
                
                for (let i = 0; i < Math.min(nombres.length, precios.length, {limite}); i++) {{
                    const nombre = nombres[i]?.textContent?.trim();
                    const precioStr = precios[i]?.getAttribute('data-internet-price');
                    
                    if (nombre && precioStr) {{
                        const precio = parseFloat(precioStr.replace(',', '.'));
                        if (precio > 0) {{
                            productos.push({{
                                nombre: nombre,
                                precio: precio
                            }});
                        }}
                    }}
                }}
                return productos;
            }}
        ''')
        
        # Formatear productos con estructura estándar
        for item in productos_data:
            productos.append({
                "nombre": item['nombre'],
                "precio": item['precio'],
                "disponible": True,
                "supermercado": "Tottus",
                "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "url": "",
                "imagen": ""
            })
            
    except Exception as e:
        print(f"Error extrayendo productos de Tottus: {e}")
    
    return productos


def _extraer_productos_makro(page, limite):
    """Extrae productos específicamente de Makro"""
    productos = []
    
    try:
        page.wait_for_timeout(2000)
        
        # Scroll para cargar contenido
        for i in range(2):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(500)
        
        # Extraer productos usando JavaScript
        productos_data = page.evaluate(f'''
            () => {{
                const productos = [];
                const elementos = document.querySelectorAll('.showcase-description');
                
                for (let i = 0; i < Math.min(elementos.length, {limite}); i++) {{
                    const elemento = elementos[i];
                    const nombreElem = elemento.querySelector('.Showcase-mk__name');
                    const precioUnitario = elemento.querySelector('.Showcase-mk__unitPrice[data-price]');
                    const precioCantidad = elemento.querySelector('.Showcase-mk__biPrice[data-price]');
                    
                    if (nombreElem) {{
                        const nombre = nombreElem.textContent.trim();
                        let precio = null;
                        
                        if (precioUnitario) {{
                            precio = parseFloat(precioUnitario.getAttribute('data-price'));
                        }} else if (precioCantidad) {{
                            precio = parseFloat(precioCantidad.getAttribute('data-price'));
                        }}
                        
                        if (nombre && precio && precio > 0) {{
                            productos.push({{
                                nombre: nombre,
                                precio: precio
                            }});
                        }}
                    }}
                }}
                return productos;
            }}
        ''')
        
        # Formatear productos con estructura estándar
        for item in productos_data:
            productos.append({
                "nombre": item['nombre'],
                "precio": item['precio'],
                "disponible": True,
                "supermercado": "Makro",
                "fecha": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "url": "",
                "imagen": ""
            })
            
    except Exception as e:
        print(f"Error extrayendo productos de Makro: {e}")
    
    return productos


def scrap_supermercado(nombre_super, termino_busqueda, limite=10):
    """
    Función principal que decide cómo scrapear según el supermercado
    
    Args:
        nombre_super (str): Nombre del supermercado
        termino_busqueda (str): Producto a buscar (requerido)
        limite (int): Máximo número de productos
    
    Returns:
        list: Lista de productos con estructura estándar
    """
    nombre_super = nombre_super.lower().strip()
    
    # Validar supermercado soportado
    supermercados_disponibles = list(SUPERMERCADOS_API.keys()) + SUPERMERCADOS_SCRAPING
    if nombre_super not in supermercados_disponibles:
        print(f"⚠️ Supermercado '{nombre_super}' no soportado.")
        print(f"Supermercados disponibles: {', '.join(supermercados_disponibles)}")
        return []
    
    # Decidir método de extracción
    if nombre_super in SUPERMERCADOS_API:
        return scrap_supermercado_api(nombre_super, termino_busqueda, limite)
    elif nombre_super in SUPERMERCADOS_SCRAPING:
        return scrap_playwright_generico(nombre_super, termino_busqueda, limite)
    else:
        return []


def scrap_todos_supermercados(termino_busqueda, limite_por_super=10):
    """
    Une todo para mostrar en dashboard - scraping paralelo optimizado
    
    Args:
        termino_busqueda (str): Producto a buscar (requerido)
        limite_por_super (int): Máximo productos por supermercado
    
    Returns:
        dict: Resultados organizados para el frontend
    """
    print(f"🔍 Iniciando búsqueda de '{termino_busqueda}' en todos los supermercados...")
    
    todos_productos = []
    resultados_por_super = {}
    
    # Lista de todos los supermercados
    supermercados = list(SUPERMERCADOS_API.keys()) + SUPERMERCADOS_SCRAPING
    
    def scrap_individual(nombre_super):
        """Función auxiliar para scraping individual"""
        print(f"📦 Procesando {nombre_super.capitalize()}...")
        productos = scrap_supermercado(nombre_super, termino_busqueda, limite_por_super)
        return nombre_super, productos
    
    # Scraping paralelo para APIs (más rápido y seguro)
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Primero las APIs
        futures_api = [
            executor.submit(scrap_individual, super_name) 
            for super_name in SUPERMERCADOS_API.keys()
        ]
        
        # Recopilar resultados de APIs
        for future in futures_api:
            try:
                nombre_super, productos = future.result(timeout=30)
                resultados_por_super[nombre_super] = productos
                todos_productos.extend(productos)
            except Exception as e:
                print(f"❌ Error en API: {e}")
    
    # Scraping secuencial para Playwright (evitar conflictos de browser)
    for super_scraping in SUPERMERCADOS_SCRAPING:
        try:
            nombre_super, productos = scrap_individual(super_scraping)
            resultados_por_super[nombre_super] = productos
            todos_productos.extend(productos)
        except Exception as e:
            print(f"❌ Error en scraping {super_scraping}: {e}")
    
    # Preparar respuesta para el frontend
    resultado_final = {
        "termino_busqueda": termino_busqueda,
        "fecha_busqueda": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "total_productos": len(todos_productos),
        "productos": todos_productos,
        "por_supermercado": resultados_por_super,
        "estadisticas": _generar_estadisticas(todos_productos)
    }
    
    print(f"✅ Búsqueda completada: {len(todos_productos)} productos encontrados")
    return resultado_final


def _generar_estadisticas(productos):
    """Genera estadísticas útiles para el frontend"""
    if not productos:
        return {}
    
    estadisticas = {
        "precio_promedio": 0,
        "precio_minimo": float('inf'),
        "precio_maximo": 0,
        "producto_mas_barato": None,
        "producto_mas_caro": None,
        "productos_por_super": {},
        "disponibles": 0
    }
    
    precios = []
    for producto in productos:
        precio = producto['precio']
        precios.append(precio)
        supermercado = producto['supermercado']
        
        # Precio mínimo y máximo
        if precio < estadisticas["precio_minimo"]:
            estadisticas["precio_minimo"] = precio
            estadisticas["producto_mas_barato"] = producto
        
        if precio > estadisticas["precio_maximo"]:
            estadisticas["precio_maximo"] = precio
            estadisticas["producto_mas_caro"] = producto
        
        # Contar por supermercado
        if supermercado not in estadisticas["productos_por_super"]:
            estadisticas["productos_por_super"][supermercado] = 0
        estadisticas["productos_por_super"][supermercado] += 1
        
        # Productos disponibles
        if producto['disponible']:
            estadisticas["disponibles"] += 1
    
    # Precio promedio
    if precios:
        estadisticas["precio_promedio"] = sum(precios) / len(precios)
    
    return estadisticas


# ================ FUNCIONES PARA EL FRONTEND ================

def buscar_producto_simple(termino, supermercado=None, limite=10):
    """
    Función simplificada para el frontend
    
    Args:
        termino (str): Producto a buscar
        supermercado (str, optional): Supermercado específico
        limite (int): Límite de productos
    
    Returns:
        dict: Respuesta JSON-friendly para el frontend
    """
    if supermercado:
        productos = scrap_supermercado(supermercado, termino, limite)
        return {
            "success": True,
            "supermercado": supermercado,
            "productos": productos,
            "total": len(productos)
        }
    else:
        resultado = scrap_todos_supermercados(termino, limite)
        return {
            "success": True,
            "resultado": resultado
        }


def obtener_supermercados_disponibles():
    """Retorna lista de supermercados soportados para el frontend"""
    return {
        "api": list(SUPERMERCADOS_API.keys()),
        "scraping": SUPERMERCADOS_SCRAPING,
        "todos": list(SUPERMERCADOS_API.keys()) + SUPERMERCADOS_SCRAPING
    }


def healthcheck():
    """Verificar que el sistema funciona correctamente"""
    try:
        # Test rápido con un supermercado API
        test_productos = scrap_supermercado("plazavea", "producto", 1)
        return {
            "status": "ok",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "test_result": len(test_productos) > 0
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "error": str(e)
        }


# ================ EJEMPLO DE USO PA TI MI KING ================
if __name__ == "__main__":
    # Ejemplo 1: Buscar en todos los supermercados
    # resultado = scrap_todos_supermercados("leche")
    # print(json.dumps(resultado, indent=2, ensure_ascii=False))
    
    # Ejemplo 2: Buscar en supermercado específico  
    # productos = scrap_supermercado("wong", "arroz")
    # print(f"Productos encontrados: {len(productos)}")
    
    # Ejemplo 3: Función para frontend
    # respuesta = buscar_producto_simple("pan", "plazavea")
    # print(json.dumps(respuesta, indent=2, ensure_ascii=False))
    
    # Ejemplo 4: Ver supermercados disponibles
    # print(obtener_supermercados_disponibles())
    
    # Ejemplo 5: Healthcheck
    # print(healthcheck())
    
    pass