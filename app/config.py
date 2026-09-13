from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name:str="AI Movie Studio"; host:str="0.0.0.0"; port:int=8000
    storage_root:Path=Path("./storage"); max_upload_mb:int=100; mock_generation:bool=True; mock_delay_seconds:float=.5; ffmpeg_binary:str="ffmpeg"
    motion_provider:str="auto"
    comfyui_url:str|None=None; comfyui_timeout_seconds:float=30; comfyui_poll_seconds:float=2
    comfyui_wan_workflow_api_path:Path=Path("./workflows/comfyui/wan2.2-animate.api.json")
    comfyui_wan_image_node:str="10"; comfyui_wan_image_field:str="image"; comfyui_wan_video_node:str="145"; comfyui_wan_video_field:str="video"
    zerogpu_space:str="alexnasa/Wan2.2-Animate-ZEROGPU"
    zerogpu_duration_seconds:int=2; zerogpu_mode:str="Pose Retarget"; zerogpu_resolution:str="Low Res"; zerogpu_timeout_seconds:float=900
    hf_token:str|None=None
    model_config=SettingsConfigDict(env_file=".env",extra="ignore",case_sensitive=False)

settings=Settings()
