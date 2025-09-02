import csv
import argparse
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Optional, Tuple, List
import os

def visualize_simulation_log(
    log_file: str, 
    output_image: str,
    figsize: Tuple[int, int] = (12, 10),
    show_setpoints: bool = True
) -> Optional[plt.Figure]:
    """
    读取模拟日志文件并生成结果图表。
    
    该函数读取仿真日志文件，创建包含水质参数（浊度和溶解氧）
    随时间变化的图表，并保存到指定路径。

    Args:
        log_file (str): 输入CSV日志文件的路径，必须包含timestamp、turbidity、
                       dissolved_oxygen等列
        output_image (str): 保存输出图表图像的路径
        figsize (Tuple[int, int]): 图表尺寸（宽度，高度），默认为(12, 10)
        show_setpoints (bool): 是否显示设定值线，默认为True
    
    Returns:
        Optional[plt.Figure]: 如果成功创建图表则返回Figure对象，否则返回None
        
    Raises:
        FileNotFoundError: 当日志文件不存在时
        ValueError: 当日志文件格式不正确或缺少必需列时
        
    Example:
        >>> fig = visualize_simulation_log(
        ...     "simulation_log.csv", 
        ...     "output_plot.png"
        ... )
        >>> if fig:
        ...     print("图表生成成功")
    """
    # 输入验证
    if not isinstance(log_file, str):
        raise TypeError("log_file must be a string")
    if not os.path.exists(log_file):
        raise FileNotFoundError(f"Log file not found: {log_file}")
    
    # 数据列表
    timestamps: List[datetime] = []
    turbidity: List[float] = []
    dissolved_oxygen: List[float] = []
    turbidity_setpoint: List[float] = []
    do_setpoint: List[float] = []

    # 从CSV读取数据
    try:
        with open(log_file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                timestamps.append(datetime.fromisoformat(row['timestamp']))
                turbidity.append(float(row['turbidity']))
                dissolved_oxygen.append(float(row['dissolved_oxygen']))
                turbidity_setpoint.append(float(row['turbidity_setpoint']))
                do_setpoint.append(float(row['do_setpoint']))

    except (IOError, FileNotFoundError) as e:
        print(f"错误：无法读取日志文件 '{log_file}'。")
        print(f"  原因：{e}")
        return
    except (ValueError, KeyError) as e:
        print(f"错误：无法解析日志文件 '{log_file}'。它可能已损坏或格式错误。")
        print(f"  原因：{e}")
        return

    if not timestamps:
        print(f"警告：日志文件 '{log_file}' 为空。未生成图表。")
        return

    # 创建图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True)
    fig.suptitle('水厂模拟结果', fontsize=16, fontweight='bold')

    # 图表1：浊度
    ax1.plot(timestamps, turbidity, label='测量浊度', color='b', linewidth=2, marker='o', markersize=3)
    if show_setpoints and turbidity_setpoint:
        ax1.plot(timestamps, turbidity_setpoint, label='浊度设定点', color='b', linestyle='--', linewidth=1)
    ax1.set_ylabel('浊度 (NTU)', fontsize=12)
    ax1.set_title('浊度控制', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 添加统计信息
    if turbidity:
        turbidity_mean = sum(turbidity) / len(turbidity)
        turbidity_std = (sum((x - turbidity_mean) ** 2 for x in turbidity) / len(turbidity)) ** 0.5
        turbidity_stats = f"均值: {turbidity_mean:.2f}, 标准差: {turbidity_std:.2f}"
        ax1.text(0.02, 0.98, turbidity_stats, transform=ax1.transAxes, 
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 图表2：溶解氧
    ax2.plot(timestamps, dissolved_oxygen, label='测量溶解氧', color='r', linewidth=2, marker='s', markersize=3)
    if show_setpoints and do_setpoint:
        ax2.plot(timestamps, do_setpoint, label='溶解氧设定点', color='r', linestyle='--', linewidth=1)
    ax2.set_xlabel('时间', fontsize=12)
    ax2.set_ylabel('溶解氧 (mg/L)', fontsize=12)
    ax2.set_title('溶解氧控制', fontsize=14)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 添加统计信息
    if dissolved_oxygen:
        do_mean = sum(dissolved_oxygen) / len(dissolved_oxygen)
        do_std = (sum((x - do_mean) ** 2 for x in dissolved_oxygen) / len(dissolved_oxygen)) ** 0.5
        do_stats = f"均值: {do_mean:.2f}, 标准差: {do_std:.2f}"
        ax2.text(0.02, 0.98, do_stats, transform=ax2.transAxes, 
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))

    # 保存图表
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    try:
        plt.savefig(output_image, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"图表已保存到 {output_image}")
    except Exception as e:
        print(f"保存图表时出错: {e}")
        return None
    
    return fig


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="可视化模拟日志数据。")
    parser.add_argument('--log-file', type=str, default='simulation_log.csv', help='输入CSV日志文件的路径。')
    parser.add_argument('--output-image', type=str, default='simulation_plot.png', help='保存输出图表图像的路径。')

    args = parser.parse_args()

    visualize_simulation_log(
        log_file=args.log_file,
        output_image=args.output_image
    )
