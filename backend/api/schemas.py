from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional
from datetime import datetime

class AlertConfigBase(BaseModel):
    umbral_minimo: int = Field(..., ge=0, description="Umbral mínimo para generar alerta de quiebre")
    umbral_sobreabastecimiento: int = Field(..., gt=0, description="Umbral para generar alerta de sobreabastecimiento")
    is_active: bool = True

    @validator('umbral_sobreabastecimiento')
    def check_umbels(cls, v, values):
        if 'umbral_minimo' in values and v <= values['umbral_minimo']:
            raise ValueError('umbral_sobreabastecimiento debe ser mayor que umbral_minimo')
        return v

class AlertConfigCreate(AlertConfigBase):
    producto_id: str = Field(..., description="ID del producto (SKU)")

class AlertConfigUpdate(AlertConfigBase):
    producto_id: str = Field(..., description="ID del producto (SKU)")
    
class AlertConfigResponse(AlertConfigBase):
    id: int
    producto_id: str
    updated_by: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True
