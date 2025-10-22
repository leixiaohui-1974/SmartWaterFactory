#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SmartWaterFactory 包安装配置文件。"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# 读取requirements.txt
def read_requirements(filename):
    """读取依赖文件。"""
    requirements = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if line and not line.startswith('#') and not line.startswith('-r'):
                requirements.append(line)
    return requirements

# 基础依赖
install_requires = read_requirements('requirements.txt')

# 开发依赖
extras_require = {
    'dev': read_requirements('requirements-dev.txt'),
}

setup(
    name='smart-water-factory',
    version='1.0.0',
    description='智能水厂控制系统 - 工业水处理过程控制仿真平台',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='SmartWaterFactory Team',
    author_email='info@smartwaterfactory.com',
    url='https://github.com/leixiaohui-1974/SmartWaterFactory',
    license='MIT',

    # 包配置
    packages=find_packages(exclude=['tests', 'tests.*', 'examples', 'examples.*']),
    include_package_data=True,

    # Python版本要求
    python_requires='>=3.9',

    # 依赖
    install_requires=install_requires,
    extras_require=extras_require,

    # 入口点
    entry_points={
        'console_scripts': [
            'water-plant-sim=run_simulation:main',
            'water-plant-viz=visualize_log:main',
            'water-plant-api=utils.api_server:run_api_server',
        ],
    },

    # 分类信息
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],

    # 关键词
    keywords=[
        'water-treatment',
        'process-control',
        'pid-controller',
        'mpc-controller',
        'simulation',
        'industrial-control',
        'sensor-fusion',
        'kalman-filter',
    ],

    # 项目URLs
    project_urls={
        'Documentation': 'https://github.com/leixiaohui-1974/SmartWaterFactory/blob/main/DOCUMENTATION.md',
        'Source': 'https://github.com/leixiaohui-1974/SmartWaterFactory',
        'Bug Reports': 'https://github.com/leixiaohui-1974/SmartWaterFactory/issues',
    },
)
