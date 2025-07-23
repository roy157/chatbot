# test_direct_gemini.py
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY no encontrada en el archivo .env")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # Usa el mismo modelo y temperatura
        model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"temperature": 0.7}) 

        user_query = "¿quiero entrenar a mi perro para que sea inteligente como lo hago?"
        print(f"Enviando solicitud directa al modelo: '{user_query}'")

        response = model.generate_content(user_query)
        print("\nRespuesta directa del modelo:")
        print(response.text)

    except Exception as e:
        print(f"\nOcurrió un error al probar la API directamente: {e}")