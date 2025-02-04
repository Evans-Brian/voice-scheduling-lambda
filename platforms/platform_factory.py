from typing import Dict, Type, Optional
from .base_platform import BookingPlatform
from .google_calendar import GoogleCalendarPlatform

class PlatformFactory:
    """Factory class for creating booking platform instances"""
    
    _platforms: Dict[str, Type[BookingPlatform]] = {
        'google': GoogleCalendarPlatform
    }
    
    @classmethod
    def get_platform(cls, platform_name: Optional[str]) -> BookingPlatform:
        """
        Get an instance of the requested platform
        
        Args:
            platform_name: String identifier for the platform
            
        Returns:
            BookingPlatform instance
            
        Raises:
            ValueError: If platform_name is not supported
        """
        if platform_name is None:
            supported = ", ".join(cls._platforms.keys())
            raise ValueError(
                f"Unsupported platform: None. "
                f"Supported platforms are: {supported}"
            )
            
        platform_class = cls._platforms.get(platform_name.lower())
        if not platform_class:
            supported = ", ".join(cls._platforms.keys())
            raise ValueError(
                f"Unsupported platform: {platform_name}. "
                f"Supported platforms are: {supported}"
            )
        return platform_class() 