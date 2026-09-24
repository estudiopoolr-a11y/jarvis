import json
import os
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pytz

# Configuración
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'google_credentials.json'
TIMEZONE = 'America/Bogota'

def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('calendar', 'v3', credentials=creds)

# Modelos Pydantic
class CrearEventoInput(BaseModel):
    titulo: str
    fecha_inicio: str
    duracion_minutos: int = 30
    descripcion: str = ""
    ubicacion: str = ""

class BuscarEventoInput(BaseModel):
    query: str
    max_resultados: int = 5

class ObtenerEventoInput(BaseModel):
    event_id: str

class ActualizarEventoInput(BaseModel):
    event_id: str
    nuevo_titulo: Optional[str] = None
    nueva_fecha_inicio: Optional[str] = None
    nueva_duracion_minutos: Optional[int] = None
    nueva_descripcion: Optional[str] = None

class EliminarEventoInput(BaseModel):
    event_id: str

# Funciones CRUD
def crear_evento(input_data: CrearEventoInput):
    service = get_calendar_service()
    start_time = datetime.fromisoformat(input_data.fecha_inicio)
    end_time = start_time + timedelta(minutes=input_data.duracion_minutos)
    
    event = {
        'summary': input_data.titulo,
        'description': input_data.descripcion,
        'location': input_data.ubicacion,
        'start': {'dateTime': start_time.isoformat(), 'timeZone': TIMEZONE},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': TIMEZONE},
    }
    return service.events().insert(calendarId='primary', body=event).execute()

def listar_proximos_eventos(max_resultados: int = 5):
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                        maxResults=max_resultados, singleEvents=True,
                                        orderBy='startTime').execute()
    return events_result.get('items', [])

def buscar_eventos(input_data: BuscarEventoInput):
    service = get_calendar_service()
    events_result = service.events().list(calendarId='primary', q=input_data.query,
                                        maxResults=input_data.max_resultados,
                                        singleEvents=True).execute()
    return events_result.get('items', [])

def obtener_evento(input_data: ObtenerEventoInput):
    service = get_calendar_service()
    return service.events().get(calendarId='primary', eventId=input_data.event_id).execute()

def actualizar_evento(input_data: ActualizarEventoInput):
    service = get_calendar_service()
    event = service.events().get(calendarId='primary', eventId=input_data.event_id).execute()
    
    if input_data.nuevo_titulo:
        event['summary'] = input_data.nuevo_titulo
    if input_data.nueva_descripcion:
        event['description'] = input_data.nueva_descripcion
    if input_data.nueva_fecha_inicio:
        start_time = datetime.fromisoformat(input_data.nueva_fecha_inicio)
        duration = input_data.nueva_duracion_minutos or 30
        end_time = start_time + timedelta(minutes=duration)
        event['start']['dateTime'] = start_time.isoformat()
        event['end']['dateTime'] = end_time.isoformat()
        
    return service.events().update(calendarId='primary', eventId=input_data.event_id, body=event).execute()

def eliminar_evento(input_data: EliminarEventoInput):
    service = get_calendar_service()
    return service.events().delete(calendarId='primary', eventId=input_data.event_id).execute()
