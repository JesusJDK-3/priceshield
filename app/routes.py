from flask import Blueprint, jsonify
from .database import get_collection

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return '<h1>Bienvenido a PriceShield</h1>'

@main.route('/productos')
def listar_productos ():
    productos = get_collection('productos')
    datos = list(productos.find({}, {'_id': 0})) #no enviar el id de mongo
    return jsonify(datos)