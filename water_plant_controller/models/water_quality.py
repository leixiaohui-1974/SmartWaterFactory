from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WaterQuality:
    """
    表示特定时间点的水质参数。
    
    这个数据类用于存储水处理过程中的关键水质指标，包括时间戳、
    pH值、浊度和溶解氧浓度。所有参数都应该在合理的物理范围内。
    
    Attributes:
        timestamp (datetime): 测量时间戳
        ph (float): pH值，通常范围为0-14，中性为7.0
        turbidity (float): 浊度值，以NTU（浊度单位）为单位，
                          通常范围为0-1000 NTU
        dissolved_oxygen (float): 溶解氧浓度，以mg/L为单位，
                                 通常范围为0-15 mg/L
    
    Example:
        >>> from datetime import datetime
        >>> quality = WaterQuality(
        ...     timestamp=datetime.now(),
        ...     ph=7.2,
        ...     turbidity=5.0,
        ...     dissolved_oxygen=8.5
        ... )
    """
    timestamp: datetime
    ph: float
    turbidity: float
    dissolved_oxygen: float
    
    def __post_init__(self) -> None:
        """
        验证水质参数的合理性。
        
        Raises:
            ValueError: 当参数超出合理范围时抛出异常
        """
        if not (0.0 <= self.ph <= 14.0):
            raise ValueError(f"pH值必须在0-14范围内，当前值: {self.ph}")
        if self.turbidity < 0.0:
            raise ValueError(f"浊度不能为负值，当前值: {self.turbidity}")
        if self.dissolved_oxygen < 0.0:
            raise ValueError(f"溶解氧不能为负值，当前值: {self.dissolved_oxygen}")
    
    def is_within_normal_range(self) -> bool:
        """
        检查水质参数是否在正常范围内。
        
        Returns:
            bool: 如果所有参数都在正常范围内返回True，否则返回False
        """
        return (
            6.5 <= self.ph <= 8.5 and
            self.turbidity <= 10.0 and
            5.0 <= self.dissolved_oxygen <= 12.0
        )
