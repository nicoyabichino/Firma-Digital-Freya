from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import datetime

app = Flask(__name__)
# Esto permite que tu GitHub Pages se conecte a esta API sin errores de CORS
CORS(app, resources={r"/*": {"origins": "*"}})

BASE_URL = "https://sanatoriorosario.titaves.com.ar/freya"

def login_freya():
    session = requests.Session()
    login_data = {'org': 'sanatoriodelrosario', 'user': 'wchatbot', 'pass': 'winston26'}
    session.post(f"{BASE_URL}/accesos/login", data=login_data, verify=False)
    return session

@app.route('/api/buscar_pacientes', methods=['GET'])
def buscar_pacientes():
    hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    url = f"{BASE_URL}/facturacion/controlatenciones?fr_time=123&estado=&medico_id=&fechaini={hoy}&fechafin={hoy}&servicio=&filtrar=1"
    
    session = login_freya()
    res = session.get(url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    pacientes = []
    for tr in soup.select("table#atenciones tbody tr[role='atencion']"):
        cols = tr.find_all("td")
        if len(cols) >= 10:
            pacientes.append({
                "id": tr.get("data-atencion"),
                "nombre": cols[4].get_text(strip=True),
                "dni": cols[5].get_text(strip=True),
                "os": cols[6].get_text(strip=True)
            })
            
    return jsonify(pacientes)

@app.route('/api/subir_pdf', methods=['POST'])
def subir_pdf():
    atencion_id = request.form.get('atencion_id')
    archivo = request.files.get('archivo')
    nombre_archivo = request.form.get('nombre_archivo', 'Documento.pdf')
    
    session = login_freya()
    
    # Extraer campos ocultos del modal
    modal_url = f"{BASE_URL}/consultorio/adjuntararchivos/{atencion_id}/1"
    res_modal = session.get(modal_url, verify=False)
    soup = BeautifulSoup(res_modal.text, 'html.parser')
    
    form = soup.find('form')
    if not form:
        return jsonify({"error": "No se halló el form"}), 400
        
    payload = {}
    for inp in form.find_all('input', type='hidden'):
        if inp.get('name'):
            payload[inp.get('name')] = inp.get('value', '')
            
    btn_add = soup.find('a', class_=lambda c: c and 'addinforme' in c)
    estudio_id = btn_add.get('data-estudioid', '') if btn_add else ""
    
    payload['tipoestudio_id[]'] = '2'
    payload['estudiopacientedicom_id[]'] = estudio_id
    payload['tituloestudio[]'] = 'Doc_Firma_Digital'
    payload['guardar'] = '1'
    
    files = {
        'archivo[]': (nombre_archivo, archivo.read(), 'application/pdf')
    }
    
    upload_url = f"{BASE_URL}/consultorio/adjuntararchivos_post"
    session.post(upload_url, data=payload, files=files, verify=False)
    
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
