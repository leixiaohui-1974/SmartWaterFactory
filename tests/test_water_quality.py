import pytest
from datetime import datetime
from water_plant_controller.models.water_quality import WaterQuality


class TestWaterQuality:
    def test_creation(self):
        """测试WaterQuality对象的创建。"""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        quality = WaterQuality(
            timestamp=timestamp,
            ph=7.0,
            turbidity=5.0,
            dissolved_oxygen=8.0
        )
        
        assert quality.timestamp == timestamp
        assert quality.ph == 7.0
        assert quality.turbidity == 5.0
        assert quality.dissolved_oxygen == 8.0
        
        # 测试字符串表示
        str_repr = str(quality)
        assert "WaterQuality" in str_repr
        assert "7.0" in str_repr
    
    def test_post_init_validation(self):
        """测试__post_init__验证"""
        timestamp = datetime.now()
        
        # 测试pH超出范围
        with pytest.raises(ValueError, match="pH值必须在0-14范围内，当前值: 15.0"):
            WaterQuality(timestamp=timestamp, ph=15.0, turbidity=1.0, dissolved_oxygen=8.0)
        
        with pytest.raises(ValueError, match="pH值必须在0-14范围内，当前值: -1.0"):
            WaterQuality(timestamp=timestamp, ph=-1.0, turbidity=1.0, dissolved_oxygen=8.0)
        
        # 测试负浊度
        with pytest.raises(ValueError, match="浊度不能为负值，当前值: -1.0"):
            WaterQuality(timestamp=timestamp, ph=7.0, turbidity=-1.0, dissolved_oxygen=8.0)
        
        # 测试负溶解氧
        with pytest.raises(ValueError, match="溶解氧不能为负值，当前值: -1.0"):
            WaterQuality(timestamp=timestamp, ph=7.0, turbidity=1.0, dissolved_oxygen=-1.0)
    
    def test_is_within_normal_range(self):
        """测试is_within_normal_range方法"""
        timestamp = datetime.now()
        
        # 测试正常范围内的值
        normal_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert normal_quality.is_within_normal_range() == True
        
        # 测试pH过低
        low_ph_quality = WaterQuality(
            timestamp=timestamp, ph=5.0, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert low_ph_quality.is_within_normal_range() == False
        
        # 测试pH过高
        high_ph_quality = WaterQuality(
            timestamp=timestamp, ph=9.5, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert high_ph_quality.is_within_normal_range() == False
        
        # 测试浊度过高
        high_turbidity_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=15.0, dissolved_oxygen=8.0
        )
        assert high_turbidity_quality.is_within_normal_range() == False
        
        # 测试溶解氧过低
        low_do_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=1.0, dissolved_oxygen=3.0
        )
        assert low_do_quality.is_within_normal_range() == False
        
        # 测试溶解氧过高
        high_do_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=1.0, dissolved_oxygen=15.0
        )
        assert high_do_quality.is_within_normal_range() == False
    
    def test_boundary_values(self):
        """测试边界值"""
        timestamp = datetime.now()
        
        # 测试pH边界值
        min_ph_quality = WaterQuality(
            timestamp=timestamp, ph=0.0, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert min_ph_quality.ph == 0.0
        
        max_ph_quality = WaterQuality(
            timestamp=timestamp, ph=14.0, turbidity=1.0, dissolved_oxygen=8.0
        )
        assert max_ph_quality.ph == 14.0
        
        # 测试零值
        zero_values_quality = WaterQuality(
            timestamp=timestamp, ph=7.0, turbidity=0.0, dissolved_oxygen=0.0
        )
        assert zero_values_quality.turbidity == 0.0
        assert zero_values_quality.dissolved_oxygen == 0.0
    
    def test_normal_range_boundaries(self):
        """测试正常范围的边界值"""
        timestamp = datetime.now()
        
        # 测试正常范围的下边界
        lower_bound_quality = WaterQuality(
            timestamp=timestamp, ph=6.5, turbidity=0.0, dissolved_oxygen=5.0
        )
        assert lower_bound_quality.is_within_normal_range() == True
        
        # 测试正常范围的上边界
        upper_bound_quality = WaterQuality(
            timestamp=timestamp, ph=8.5, turbidity=4.0, dissolved_oxygen=12.0
        )
        assert upper_bound_quality.is_within_normal_range() == True
