try:
    from src.config.settings import Settings, get_settings, reload_settings, settings
except ModuleNotFoundError:
    from config.settings import Settings, get_settings, reload_settings, settings

__all__ = ["Settings", "get_settings", "reload_settings", "settings"]
