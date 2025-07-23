# models.py
from pydantic import BaseModel, Field
from typing import Optional, List

# Modelo Pydantic de ejemplo para extraer información general de mascotas
class PetInfo(BaseModel):
    """Información estructurada sobre una mascota."""
    type: str = Field(description="Tipo de mascota (e.g., 'perro', 'gato').")
    name: Optional[str] = Field(None, description="Nombre de la mascota, si se menciona.")
    breed: Optional[str] = Field(None, description="Raza de la mascota.")
    age_years: Optional[int] = Field(None, description="Edad de la mascota en años.")
    health_concern: Optional[str] = Field(None, description="Preocupación de salud o síntoma que la mascota podría tener.")

# Modelo Pydantic de ejemplo para recomendar una raza
class BreedRecommendation(BaseModel):
    """Recomendación de una raza de perro o gato basada en criterios dados."""
    animal_type: str = Field(description="Tipo de animal (perro o gato) para la recomendación.")
    recommended_breed: str = Field(description="La raza de perro o gato recomendada.")
    reasoning: str = Field(description="Justificación detallada de por qué se recomienda esta raza.")
    key_characteristics: List[str] = Field(description="Características clave de la raza recomendada.")

# Un modelo de salida estructurada más general para las respuestas del chat principal
class StructuredChatOutput(BaseModel):
    """Estructura general para la respuesta del chatbot, que puede incluir datos estructurados y texto libre."""
    text_response: str = Field(description="La parte principal de la respuesta del chatbot en texto libre.")
    extracted_entities: Optional[PetInfo] = Field(None, description="Información estructurada de mascotas, si es relevante.")
    action_required: Optional[str] = Field(None, description="Una acción sugerida para el chatbot (e.g., 'ask_for_clarification', 'provide_resource').")