from pydantic import BaseModel

class ThingsboardConfig(BaseModel):
    device_token: str
    host: str
    port: int

class SerialConfig(BaseModel):
    puerto: str

class RelayConfig(BaseModel):
    pin: int
    high_time: int
    low_time: int
    
class RelayMonitorConfig(BaseModel):
    alarm_pin: int
    trouble_pin: int
    publish_interval: int
    alarm_active_high: bool
    trouble_active_high: bool

class SilenceRelayConfig(BaseModel):
    pin: int
    activation_time: int  # Tiempo en segundos que el relay estará activo
    active_high: bool  # True si el relay se activa con HIGH, False si se activa con LOW

class ResetRelayConfig(BaseModel):
    pin: int
    activation_time: int  # Tiempo en segundos que el relay estará activo
    active_high: bool  # True si el relay se activa con HIGH, False si se activa con LOW

class ConfigSchema(BaseModel):
    thingsboard: ThingsboardConfig
    serial: SerialConfig
    relay: RelayConfig
    relay_monitor: RelayMonitorConfig
    silence_relay: SilenceRelayConfig
    reset_relay: ResetRelayConfig
    id_modelo_panel: int
