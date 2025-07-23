# chatbot_logic.py (Parte donde se define la extracción estructurada)
structured_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            "Eres un asistente que extrae información estructurada sobre mascotas de un texto. "
            "La información debe ser en formato JSON siguiendo el esquema proporcionado. "
            "Si un campo no está presente, déjalo como null. {format_instructions}"
        ),
        HumanMessage(content="{input}")
    ]
)
json_parser = JsonOutputParser(pydantic_object=PetInfo)
structured_extraction_chain = (
    structured_prompt.partial(format_instructions=json_parser.get_format_instructions())
    | llm.with_structured_output(schema=PetInfo)
)

# models.py (Definición de cómo debe ser la información de la mascota)
class PetInfo(BaseModel):
    """Información estructurada sobre una mascota."""
    type: str = Field(description="Tipo de mascota (e.g., 'perro', 'gato').")
    name: Optional[str] = Field(None, description="Nombre de la mascota, si se menciona.")
    breed: Optional[str] = Field(None, description="Raza de la mascota.")
    age_years: Optional[int] = Field(None, description="Edad de la mascota en años.")
    health_concern: Optional[str] = Field(None, description="Preocupación de salud o síntoma que la mascota podría tener.")