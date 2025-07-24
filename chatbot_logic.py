# chatbot_logic.py
import os
from langchain_openai import ChatOpenAI # Usaremos esta para Groq

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Any, AsyncGenerator

from dotenv import load_dotenv
load_dotenv()

# Asegúrate de que GROQ_API_KEY esté configurada
if not os.getenv("GROQ_API_KEY"):
    raise ValueError("La variable de entorno GROQ_API_KEY no está configurada.")

from models import PetInfo, BreedRecommendation, StructuredChatOutput

# Inicializa el LLM para Groq Cloud (llama3-8b-8192)
llm = ChatOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1", # URL específica de la API de Groq
    model="llama3-8b-8192", # Modelo de LLaMA 3 de Groq.
                           # Opcional: Podrías probar "mixtral-8x7b-32768" si lo prefieres para más potencia.
    temperature=0.5, # Un buen punto de partida para este modelo
)

chat_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            """Eres el 'Asistente de Mascotas', un chatbot amable y servicial, especializado **EXCLUSIVAMENTE en perros y gatos**.
Tu objetivo principal es **proporcionar información útil y directa** sobre el cuidado, salud, comportamiento y razas de perros y gatos.

**DIRECTRICES CLAVE PARA TODAS LAS INTERACCIONES (EXCEPTO SALUDO INICIAL QUE MANEJA EL MAIN.PY):**

* **Mantén el contexto de la conversación en todo momento.** Cada respuesta debe estar directamente relacionada con la pregunta actual del usuario y con la información previa del diálogo.
* **Sé siempre directo y útil.** Responde a la pregunta del usuario con la información solicitada.
* **Evita pedir información que ya se te haya proporcionado o que sea evidente por el contexto.**
* **Sé conciso pero completo.**
* **Si la consulta NO es sobre perros o gatos, indica amablemente que tu conocimiento se limita a estos animales y redirige la conversación.**
* **Para temas de seguridad o inapropiados, rechaza la solicitud de forma firme pero amable y redirige al bienestar animal.**

**Tu meta es ser el asistente más útil, claro y conversacional posible.**
"""
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        HumanMessage(content="{input}")
    ]
)

# La sección structured_extraction_chain está ACTIVA
structured_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            "Eres un asistente que extrae información estructurada sobre mascotas de un texto. "
            "La información debe ser en formato JSON siguiendo el esquema proporcionado. "
            "NO añadas texto adicional, explicaciones o comentarios. Si un campo no está presente, déjalo como null. "
            "EL ÚNICO CONTENIDO DE TU RESPUESTA DEBE SER EL OBJETO JSON. {format_instructions}"
        ),
        HumanMessage(content="{input}")
    ]
)
json_parser = JsonOutputParser(pydantic_object=PetInfo)

structured_extraction_chain = (
    structured_prompt.partial(format_instructions=json_parser.get_format_instructions())
    | llm.with_structured_output(schema=PetInfo) # Esto funciona con ChatOpenAI (Groq)
)

def process_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae el 'input' y convierte el historial de chat a formato de mensaje de LangChain."""
    user_input = input_data.get("input", "")
    history = input_data.get("chat_history", [])
    
    formatted_history = []
    for msg in history:
        if msg.get("role") == "user":
            formatted_history.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            formatted_history.append(AIMessage(content=msg.get("content", "")))
    
    return {"input": user_input, "chat_history": formatted_history}

conversational_chain = (
    RunnableLambda(process_input)
    | chat_prompt
    | llm
)

# parallel_chain está ACTIVA
parallel_chain = RunnableParallel(
    general_response=conversational_chain,
    extracted_data=structured_extraction_chain
)

async def get_chatbot_response_stream(messages: List[Dict[str, Any]], temperature: float) -> AsyncGenerator[str, None]:
    input_message = ""
    chat_history_for_chain = []
    if messages:
        input_message = messages[-1]["content"]
        chat_history_for_chain = messages[:-1]

    chain_input = {"input": input_message, "chat_history": chat_history_for_chain}

    async for chunk in conversational_chain.astream(chain_input, {"configurable": {"llm_temperature": temperature}}):
        if hasattr(chunk, 'content'):
            yield f"data: {chunk.content}\n\n"
        elif isinstance(chunk, dict) and 'answer' in chunk:
             yield f"data: {chunk['answer']}\n\n"
    yield "data: [DONE]\n\n"

async def get_chatbot_response_json(messages: List[Dict[str, Any]], temperature: float) -> Dict[str, Any]:
    input_message = ""
    chat_history_for_chain = []
    if messages:
        input_message = messages[-1]["content"]
        chat_history_for_chain = messages[:-1]

    chain_input = {"input": input_message, "chat_history": chat_history_for_chain}

    response = await conversational_chain.ainvoke(chain_input, {"configurable": {"llm_temperature": temperature}})
    
    return {
        "id": f"chatcmpl-{os.urandom(16).hex()}",
        "object": "chat.completion",
        "created": int(os.times().elapsed),
        "model": "llama3-8b-8192", # Coincide con el modelo de Groq
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response.content
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }

# Funciones get_structured_pet_info y get_parallel_responses están ACTIVAS
async def get_structured_pet_info(text: str) -> PetInfo:
    return await structured_extraction_chain.ainvoke({"input": text})

async def get_parallel_responses(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    input_message = ""
    chat_history_for_chain = []
    if messages:
        input_message = messages[-1]["content"]
        chat_history_for_chain = messages[:-1]
    
    chain_input = {"input": input_message, "chat_history": chat_history_for_chain}
    return await parallel_chain.ainvoke(chain_input)