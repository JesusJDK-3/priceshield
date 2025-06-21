# priceshield
Detector inteligente de manipulación de precios en supermercados


# 🛡️ PriceShield - Detector Inteligente de Manipulación de Precios

**PriceShield** es una plataforma web que analiza los precios de productos de supermercados para detectar anomalías y posibles manipulaciones, usando scraping, análisis estadístico y visualización de datos.

## 📌 Objetivo

Brindar a los consumidores peruanos una herramienta para monitorear el comportamiento de precios de productos y alertar cuando se detectan cambios sospechosos o injustificados.

---

## 🧰 Tecnologías utilizadas

| Área         | Herramientas                                               |
|--------------|------------------------------------------------------------|
| Backend      | Python 3, Flask, MongoDB Atlas, BeautifulSoup, pandas     |
| Frontend     | HTML, CSS, Bootstrap, Chart.js, JavaScript puro           |
| Visualización| Chart.js                                                   |
| Despliegue   | Render.com (free hosting), GitHub                          |
| Control de versiones | Git + GitHub                                      |

---

## 📁 Estructura del Proyecto


---

## ⚙️ Instalación y ejecución

```bash
# Clona el repositorio
git clone https://github.com/TU_USUARIO/priceshield.git
cd priceshield

# (Recomendado) Crea un entorno virtual
python -m venv venv
venv\Scripts\activate

# Instala las dependencias
pip install -r requirements.txt

# Ejecuta el servidor Flask
flask run
