from pathlib import Path
from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
 app_name:str="AI Movie Studio"; host:str="0.0.0.0"; port:int=8000
 storage_root:Path=Path("./storage"); max_upload_mb:int=100; mock_generation:bool=True; mock_delay_seconds:float=.5; ffmpeg_binary:str="ffmpeg"
 comfyui_url:str|None=None; comfyui_timeout_seconds:float=30; comfyui_poll_seconds:float=2
 comfyui_wan_workflow_api_path:Path=Path("./workflows/comfyui/wan2.2-animate.api.json")
 comfyui_wan_image_node:str="10"; comfyui_wan_image_field:str="image"; comfyui_wan_video_node:str="145"; comfyui_wan_video_field:str="video"
 model_config=SettingsConfigDict(env_file=".env",extra="ignore",case_sensitive=False)
settings=Settings()
