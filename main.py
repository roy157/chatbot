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
    input_message_for_comparison = "" # <-- Nueva variable para la comparación limpia
    if messages and messages[-1].get("role") == "user":
        # Usamos el input original para pasar al LLM
        input_message = messages[-1]["content"]
        # Creamos una versión limpia para las comparaciones de pre-procesamiento
        input_message_for_comparison = input_message.lower().strip().replace("?", "").replace("¿", "").replace("!", "").replace(".", "")

    # --- Lógica de pre-procesamiento: SOLO SALUDO INICIAL ---
    saludos_simples = ["hola", "qué tal", "buenos días", "buenas tardes", "buenas noches", "saludos"]
    if input_message_for_comparison in saludos_simples and len(messages) == 1: # Solo si es el primer mensaje del usuario
        fixed_response_text = "¡Hola! Soy tu Asistente de Mascotas. ¡Qué alegría verte! ¿En qué puedo ayudarte hoy sobre perros, gatos o cualquier otra mascota?"
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

    # --- CAMBIOS AQUÍ: INTERCEPTAR MÁS PREGUNTAS FRECUENTES CON RESPUESTAS FIJAS ---
    # Esto evitará que el LLM tenga que procesar estos casos que está manejando mal.
    # No queremos que el LLM se confunda con estas preguntas básicas.

    fixed_response_text_for_more_cases = None

    # Preguntas sobre el conocimiento del bot (e.g., "¿conoces perros?")
    conocimiento_preguntas = [
        "conoces perros", "sabes sobre perros", "conoces mascotas", "sabes sobre mascotas",
        "que sabes de perros", "que sabes de gatos", "eres un bot de mascotas",
        "dime sobre perros", "hablame de perros", "informacion sobre perros",
        "conoces gatos", "sabes sobre gatos", "dime sobre gatos", "hablame de gatos"
    ]
    if input_message_for_comparison in conocimiento_preguntas:
        fixed_response_text_for_more_cases = "¡Claro que sí! Mi especialidad son los perros y los gatos. Estoy aquí para ayudarte con cualquier duda sobre su cuidado, salud, comportamiento o razas. ¿Tienes una pregunta específica?"

    # Preguntas de cuidado general (e.g., "¿como cuidar un chihuahua?")
    if fixed_response_text_for_more_cases is None and \
       ("como cuidar" in input_message_for_comparison or "cuidar a" in input_message_for_comparison or "cuidado de" in input_message_for_comparison or "que comen" in input_message_for_comparison or "quiero bañarlo" in input_message_for_comparison) and \
       ("perro" in input_message_for_comparison or "gato" in input_message_for_comparison or "chihuahua" in input_message_for_comparison): # Puedes añadir más razas aquí

        mascota_identificada = ""
        if "chihuahua" in input_message_for_comparison: mascota_identificada = "Chihuahua"
        elif "perro" in input_message_for_comparison: mascota_identificada = "perro"
        elif "gato" in input_message_for_comparison: mascota_identificada = "gato"

        if "que comen" in input_message_for_comparison:
             fixed_response_text_for_more_cases = f"La alimentación de un {mascota_identificada} es muy importante. Necesitan una dieta balanceada de alta calidad, adecuada a su edad y tamaño. Es crucial evitar ciertos alimentos tóxicos como chocolate, uvas o cebolla. ¿Te gustaría saber más sobre un alimento específico o sobre porciones?"
        elif "quiero bañarlo" in input_message_for_comparison:
             fixed_response_text_for_more_cases = f"¡Claro! Bañar a un {mascota_identificada} puede ser una buena experiencia si se hace con calma. Necesitarás un champú específico para perros, agua tibia y mucha paciencia. ¿Te gustaría que te diera consejos sobre cómo hacerlo de forma segura o qué productos usar?"
        else: # Si es una pregunta general de cuidado
            fixed_response_text_for_more_cases = f"¡Excelente pregunta! Cuidar a un {mascota_identificada} implica aspectos como alimentación adecuada, ejercicio, visitas al veterinario y mucho cariño. Para darte los mejores consejos, ¿podrías contarme qué edad tiene o si tiene alguna necesidad especial?"

    # Si fixed_response_text_for_more_cases fue asignado, lo devolvemos
    if fixed_response_text_for_more_cases:
        response_content = {
            "id": f"chatcmpl-{os.urandom(16).hex()}", "object": "chat.completion",
            "created": int(os.times().elapsed), "model": "fixed-response-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": fixed_response_text_for_more_cases}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        if stream:
            async def generate_fixed_response():
                yield f"data: {fixed_response_text_for_more_cases}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(generate_fixed_response(), media_type="text/event-stream")
        else:
            return JSONResponse(content=response_content)

    # --- Fin de las nuevas reglas de pre-procesamiento ---

    # Si no es un saludo inicial y no cae en las reglas de pre-procesamiento extendidas, TODO va directamente al LLM.
    if stream:
        return StreamingResponse(get_chatbot_response_stream(messages, temperature), media_type="text/event-stream")
    else:
        response_content = await get_chatbot_response_json(messages, temperature)
        return JSONResponse(content=response_content)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")