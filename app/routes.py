# routes.py
from flask import Blueprint, jsonify, request
from .scraper import scrap_supermercado, scrap_todos_supermercados

main = Blueprint('main', __name__)

@main.route('/scrapear/<supermercado>', methods=['GET'])
def scrapear(supermercado):
    """Endpoint para scrapear un supermercado específico"""
    # Obtener parámetros
    termino_busqueda = request.args.get('q', 'aceite')
    url_base = request.args.get('url', None)  # Para supermercados nuevos
    
    try:
        productos = scrap_supermercado(supermercado, termino_busqueda, url_base)
        
        if not productos:
            return jsonify({
                "supermercado": supermercado.capitalize(),
                "termino_busqueda": termino_busqueda,
                "total_productos": 0,
                "productos": [],
                "mensaje": "No se encontraron productos. Si es un supermercado nuevo, proporciona la URL base con ?url=https://ejemplo.com"
            }), 200
        
        return jsonify({
            "supermercado": supermercado.capitalize(),
            "termino_busqueda": termino_busqueda,
            "total_productos": len(productos),
            "productos": productos
        }), 200
    except Exception as e:
        return jsonify({
            "error": f"Error scrapeando {supermercado}: {str(e)}"
        }), 500

@main.route('/scrapear/todos', methods=['GET'])
def scrapear_todos():
    """Endpoint para scrapear todos los supermercados"""
    # Obtener término de búsqueda opcional
    termino_busqueda = request.args.get('q', 'aceite')
    
    try:
        productos = scrap_todos_supermercados(termino_busqueda)
        
        # Agrupar por supermercado para estadísticas
        estadisticas = {}
        for producto in productos:
            super_name = producto['supermercado']
            if super_name not in estadisticas:
                estadisticas[super_name] = 0
            estadisticas[super_name] += 1
        
        return jsonify({
            "termino_busqueda": termino_busqueda,
            "total_productos": len(productos),
            "estadisticas": estadisticas,
            "productos": productos
        }), 200
    except Exception as e:
        return jsonify({
            "error": f"Error scrapeando todos los supermercados: {str(e)}"
        }), 500

@main.route('/supermercados', methods=['GET'])
def listar_supermercados():
    """Endpoint para listar supermercados disponibles"""
    return jsonify({
        "supermercados_disponibles": [
            {"nombre": "plazavea", "metodo": "API REST"},
            {"nombre": "wong", "metodo": "API REST"},
            {"nombre": "metro", "metodo": "API REST"},
            {"nombre": "tottus", "metodo": "Web Scraping"}
        ]
    }), 200