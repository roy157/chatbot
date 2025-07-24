# main.py
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any, List
import os
import nest_asyncio
import asyncio
from fastapi.middleware.cors import CORSMiddleware

from chatbot_logic import get_chatbot_response_stream, get_chatbot_response_json
from models import StructuredChatOutput

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "null",
    "http://localhost:5500",
    "http://127.0.0.1:5500"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nest_asyncio.apply()

@app.get("/")
async def root():
    return {"message": "¡Bienvenido a la API de Chatbot de Mascotas! Usa /chat para interactuar."}

@app.post("/chat")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    temperature = body.get("temperature", 0.5)

    input_message = ""
    # Se usa el input original para pasar al LLM en el historial
    # Se crea una versión limpia para las comparaciones de pre-procesamiento
    input_message_original_from_frontend = "" 
    input_message_for_comparison = ""

    if messages and messages[-1].get("role") == "user":
        input_message_original_from_frontend = messages[-1]["content"]
        input_message_for_comparison = input_message_original_from_frontend.lower().strip().replace("?", "").replace("¿", "").replace("!", "").replace(".", "").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u") # Normalizar acentos y signos de puntuación

    # --- Lógica de pre-procesamiento: Intercepta respuestas fijas para casos comunes ---
    # Esto asegura que el bot dé una respuesta fija y predecible al iniciar la conversación
    # y para preguntas muy directas que el LLM podría malinterpretar.

    fixed_response_text = None 
    
    # 1. Saludos Simples (solo en el primer mensaje del usuario)
    saludos_simples = ["hola", "que tal", "buenos dias", "buenas tardes", "buenas noches", "saludos"]
    if input_message_for_comparison in saludos_simples and len(messages) == 1:
        fixed_response_text = "¡Hola! Soy tu Asistente de Mascotas. ¡Qué alegría verte! ¿En qué puedo ayudarte hoy sobre perros, gatos o cualquier otra mascota?"
    
    # 2. Preguntas sobre el conocimiento del bot (e.g., "¿conoces perros?")
    conocimiento_preguntas = [
        "conoces perros", "sabes sobre perros", "conoces mascotas", "sabes sobre mascotas",
        "que sabes de perros", "que sabes de gatos", "eres un bot de mascotas",
        "dime sobre perros", "hablame de perros", "informacion sobre perros",
        "conoces gatos", "sabes sobre gatos", "dime sobre gatos", "hablame de gatos",
        "perros o gatos", "perros", "gatos", "mascotas" # Añadido "perros o gatos", "perros", "gatos", "mascotas"
    ]
    if fixed_response_text is None and input_message_for_comparison in conocimiento_preguntas:
        fixed_response_text = "¡Claro que sí! Mi especialidad son los perros y los gatos. Estoy aquí para ayudarte con cualquier duda sobre su cuidado, salud, comportamiento o razas. ¿Tienes una pregunta específica?"

    # 3. Preguntas de cuidado general (e.g., "¿como cuidar un chihuahua?")
    if fixed_response_text is None and \
       ("como cuidar" in input_message_for_comparison or "cuidar a" in input_message_for_comparison or "cuidado de" in input_message_for_comparison or "que comen" in input_message_for_comparison or "quiero bañarlo" in input_message_for_comparison):
        
        mascota_identificada = ""
        # Buscar la mascota en el input_message_original_from_frontend para ser más preciso
        if "chihuahua" in input_message_original_from_frontend.lower(): mascota_identificada = "Chihuahua"
        elif "pitbull" in input_message_original_from_frontend.lower(): mascota_identificada = "Pitbull"
        elif "labrador" in input_message_original_from_frontend.lower(): mascota_identificada = "Labrador"
        elif "perro" in input_message_original_from_frontend.lower(): mascota_identificada = "perro"
        elif "gato" in input_message_original_from_frontend.lower(): mascota_identificada = "gato"

        if "que comen" in input_message_for_comparison:
             fixed_response_text = f"La alimentación de un {mascota_identificada if mascota_identificada else 'perro o gato'} es muy importante. Necesitan una dieta balanceada de alta calidad, adecuada a su edad y tamaño. Es crucial evitar ciertos alimentos tóxicos como chocolate, uvas o cebolla. ¿Te gustaría saber más sobre un alimento específico o sobre porciones?"
        elif "quiero bañarlo" in input_message_for_comparison:
             fixed_response_text = f"¡Claro! Bañar a un {mascota_identificada if mascota_identificada else 'perro o gato'} puede ser una buena experiencia si se hace con calma. Necesitarás un champú específico para mascotas, agua tibia y mucha paciencia. ¿Te gustaría que te diera consejos sobre cómo hacerlo de forma segura o qué productos usar?"
        else: # Si es una pregunta general de cuidado
            fixed_response_text = f"¡Excelente pregunta! Cuidar a un {mascota_identificada if mascota_identificada else 'perro o gato'} implica aspectos como alimentación adecuada, ejercicio, visitas al veterinario y mucho cariño. Para darte los mejores consejos, ¿podrías contarme qué edad tiene o si tiene alguna necesidad especial?"
    
    # 4. Preguntas de adopción
    if fixed_response_text is None and ("quiero adoptar" in input_message_for_comparison or "adoptar un" in input_message_for_comparison):
        fixed_response_text = "¡Excelente decisión! Adoptar una mascota es una experiencia gratificante. Para ayudarte a encontrar al compañero perfecto, ¿podrías decirme qué tipo de mascota te gustaría (perro o gato), qué tamaño prefieres y cuál es tu estilo de vida (activo, tranquilo)?"
    
    # 5. Preguntas de definición de raza
    if fixed_response_text is None and ("que es un" in input_message_for_comparison or "que es el" in input_message_for_comparison or "que es la" in input_message_for_comparison) and \
       ("pitbull" in input_message_for_comparison or "chihuahua" in input_message_for_comparison or "labrador" in input_message_for_comparison or "perro" in input_message_for_comparison or "gato" in input_message_for_comparison):
        mascota_identificada = ""
        if "pitbull" in input_message_for_comparison: mascota_identificada = "Pitbull"
        elif "chihuahua" in input_message_for_comparison: mascota_identificada = "Chihuahua"
        elif "labrador" in input_message_for_comparison: mascota_identificada = "Labrador"
        elif "perro" in input_message_for_comparison: mascota_identificada = "perro"
        elif "gato" in input_message_for_comparison: mascota_identificada = "gato"
        fixed_response_text = f"Un {mascota_identificada} es una raza de perro (o gato) conocida por su [menciona una o dos características clave, por ejemplo: lealtad y energía en el caso del Pitbull]. ¿Te gustaría saber más sobre sus características, cuidados o comportamiento?"

    # Si una respuesta fija fue generada, la devolvemos inmediatamente.
    if fixed_response_text:
        response_content = {
            "id": f"chatcmpl-{os.urandom(16).hex()}", "object": "chat.completion",
            "created": int(os.times().elapsed), "model": "fixed-response-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": fixed_response_text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        if stream:
            async def generate_fixed_response():
                yield f"data: {fixed_response_text}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(generate_fixed_response(), media_type="text/event-stream")
        else:
            return JSONResponse(content=response_content)

    # --- Fin de la lógica de pre-procesamiento ---

    # Si no es un saludo inicial, TODO va directamente al LLM.
    # El LLM es el responsable de mantener el contexto y seguir las instrucciones del SystemMessage.
    if stream:
        return StreamingResponse(get_chatbot_response_stream(messages, temperature), media_type="text/event-stream")
    else:
        response_content = await get_chatbot_response_json(messages, temperature)
        return JSONResponse(content=response_content)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")