# check_models.py
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Carga la clave API desde el archivo .env
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY no encontrada en el archivo .env")
else:
    try:
        genai.configure(api_key=api_key)
        print("Modelos disponibles que soportan 'generateContent':")
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Ocurrió un error al listar los modelos: {e}")