from flask import Flask, render_template, request
import pandas as pd
import openai
import folium
from folium.plugins import HeatMap

app = Flask(__name__)

# Configura tu clave de API de OpenAI
api_key = 'sk-proj-CwDMh5OWyk10N3IgSyAPT3BlbkFJ9HPDxOekd1bu9dVNwk2s'
client = openai.OpenAI(api_key=api_key)

# Leer el archivo CSV
file_path = 'SIDPOL_2019_Violencia_familiar.csv'
data = pd.read_csv(file_path)

# Extraer las ciudades, tipos de denuncia y modalidades
ciudades = data['DPTO_CIA'].dropna().unique()
tipos_denuncia = data['TIPO'].dropna().unique()
modalidades = data['MODALIDAD'].dropna().unique()

# Palabras clave para reconocer modalidades
modalidades_palabras_clave = {
    'AMENAZA GRAVE': ['amenaza', 'amenazando', 'intimidación'],
    'COACCION GRAVE': ['coacción', 'forzado', 'obligado'],
    'MALTRATO SIN LESION': ['maltrato', 'insulto', 'abuso verbal'],
    'VIOLENCIA ECONOMICA O PATRIMONIAL': ['económica', 'patrimonial', 'dinero'],
    'VIOLENCIA FISICA': ['golpe', 'golpeado', 'lesión'],
    'VIOLENCIA FISICA Y PSICOLOGICA': ['golpe', 'psicológica', 'abuso'],
    'VIOLENCIA PSICOLOGICA': ['psicológica', 'acosado', 'amenaza']
}

# Agregar coordenadas manualmente
coordenadas_ciudades = {
    'AMAZONAS': [-6.2315, -77.8690],
    'ÁNCASH': [-9.5298, -77.5299],
    'APURÍMAC': [-13.6355, -72.8816],
    'AREQUIPA': [-16.4090, -71.5375],
    'AYACUCHO': [-13.1588, -74.2236],
    'CAJAMARCA': [-7.1638, -78.5003],
    'CALLAO': [-12.0553, -77.1188],
    'CUSCO': [-13.5319, -71.9675],
    'HUANCAVELICA': [-12.7877, -74.9734],
    'HUÁNUCO': [-9.9306, -76.2422],
    'ICA': [-14.0678, -75.7286],
    'JUNÍN': [-11.5410, -74.8770],
    'LA LIBERTAD': [-8.1150, -79.0285],
    'LAMBAYEQUE': [-6.7766, -79.8446],
    'LIMA': [-12.0464, -77.0428],
    'LORETO': [-3.7491, -73.2538],
    'MADRE DE DIOS': [-12.5933, -69.1890],
    'MOQUEGUA': [-17.1983, -70.9357],
    'PASCO': [-10.4069, -76.5155],
    'PIURA': [-5.1945, -80.6328],
    'PUNO': [-15.8402, -70.0219],
    'SAN MARTÍN': [-6.4851, -76.3690],
    'TACNA': [-18.0146, -70.2530],
    'TUMBES': [-3.5669, -80.4515],
    'UCAYALI': [-8.3791, -74.5539]
}

def extraer_informacion_con_openai(mensaje):
    prompt = f"Extrae la ciudad, el tipo de denuncia y la modalidad del siguiente mensaje:\n\n'{mensaje}'\n\nDevuelve la información en el formato: Ciudad: [ciudad], Tipo de denuncia: [tipo_denuncia], Modalidad: [modalidad]."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente que ayuda a identificar información relevante de los mensajes de los usuarios."},
            {"role": "user", "content": prompt}
        ]
    )
    respuesta = response.choices[0].message.content.strip()
    
    ciudad = None
    tipo_denuncia = None
    modalidad = None
    for c in ciudades:
        if c.lower() in respuesta.lower():
            ciudad = c
            break
    for t in tipos_denuncia:
        if t.lower() in respuesta.lower():
            tipo_denuncia = t
            break
    for m, palabras in modalidades_palabras_clave.items():
        for palabra in palabras:
            if palabra.lower() in respuesta.lower():
                modalidad = m
                break
        if modalidad:
            break
    return ciudad, tipo_denuncia, modalidad

def encontrar_comisaria_en_ciudad(ciudad, data):
    comisarias_ciudad = data[data['DPTO_CIA'].str.lower() == ciudad.lower()]
    if not comisarias_ciudad.empty:
        comisaria = comisarias_ciudad.iloc[0]
        return {
            'nombre': comisaria['COMISARIA'],
            'direccion': comisaria['DIRECCION'],
            'ciudad': comisaria['DPTO_CIA'],
        }
    return None

def procesar_mensaje_usuario(mensaje, ciudades, tipos_denuncia, modalidades, data):
    ciudad, tipo_denuncia, modalidad = extraer_informacion_con_openai(mensaje)
    if not ciudad:
        return {"error": "No se pudo determinar la ciudad a partir del mensaje."}
    
    comisaria = encontrar_comisaria_en_ciudad(ciudad, data)
    if not comisaria:
        return {"error": "No se encontró una comisaría en la ciudad mencionada."}
    
    prompt = f"Soy un ciudadano de {ciudad}. Mi denuncia es sobre {tipo_denuncia} con modalidad {modalidad}. ¿Qué debo hacer?"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente especializado en proporcionar información sobre el proceso de denuncia de violencia familiar en Perú. Tu objetivo es guiar a los ciudadanos a través de los pasos necesarios y ofrecerles recursos y apoyo adecuado. Responde en un parrafo sin formato para que no aparescan los asteriscos al copiar."},
            {"role": "user", "content": prompt}
        ]
    )
    return {
        "ciudad": ciudad,
        "tipo_denuncia": tipo_denuncia,
        "modalidad": modalidad,
        "comisaria": comisaria,
        "respuesta": response.choices[0].message.content.strip()
    }

def generar_mapa_de_calor(data):
    # Crear un mapa centrado en Perú
    mapa = folium.Map(location=[-9.19, -75.0152], zoom_start=5)

    # Crear una lista de coordenadas para el mapa de calor
    coordenadas = []
    for index, row in data.iterrows():
        ciudad = row['DPTO_CIA']
        if ciudad in coordenadas_ciudades:
            coordenadas.append(coordenadas_ciudades[ciudad])

    # Agregar las coordenadas al mapa de calor
    HeatMap(coordenadas).add_to(mapa)

    # Guardar el mapa en un archivo HTML
    mapa.save('templates/mapa_de_calor.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    generar_mapa_de_calor(data)  # Generar el mapa de calor cada vez que se carga la página
    if request.method == 'POST':
        mensaje = request.form['mensaje']
        resultado = procesar_mensaje_usuario(mensaje, ciudades, tipos_denuncia, modalidades, data)
        return render_template('index.html', resultado=resultado)
    return render_template('index.html')

@app.route('/mapa')
def mapa():
    return render_template('mapa_de_calor.html')

if __name__ == '__main__':
    app.run(debug=True)