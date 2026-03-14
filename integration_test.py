# -*- coding: utf-8 -*-
"""
TGWCollector 集成测试
测试与模拟TGW服务器的完整交互流程
"""

import asyncio
import sys
import os
import time
from io import StringIO

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tgwMonitor import TGWCollector
from mock_tgw_server import MockTGWServer

def run_integration_test():
    """运行集成测试"""
    print("=== TGWCollector 集成测试 ===")
    
    # 1. 创建测试配置文件
    config_content = """[gateway]
host = 127.0.0.1
port = 7000
password = your_password
tgw_id = W123456Y0001

[collector]
interval = 1
heartbeat_interval = 5
timeout = 2.0
retry_interval = 1

[telegraf]
debug = true
"""
    
    with open('test_integration_config.ini', 'w') as f:
        f.write(config_content)
    
    # 2. 启动模拟服务器（在后台运行）
    import subprocess
    import time
    
    server_process = subprocess.Popen(
        [sys.executable, 'mock_tgw_server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(3)
    
    # 检查服务器是否成功启动
    if server_process.poll() is not None:
        stdout, stderr = server_process.communicate()
        print("服务器启动失败!")
        print("stdout:", stdout)
        print("stderr:", stderr)
        return
    
    print("模拟服务器已启动")
    
    # 3. 运行TGWCollector进行测试
    print("\n=== 运行TGWCollector测试 ===")
    
    # 使用 -u 参数运行 Python 以禁用输出缓冲
    collector_process = subprocess.Popen(
        ["python", "-u", "tgwMonitor.py", "-c", "test_integration_config.ini"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # 运行8秒后停止
    time.sleep(8)
    collector_process.terminate()
    
    # 读取输出
    try:
        stdout, stderr = collector_process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        stdout, stderr = collector_process.communicate()
    
    print("\n=== 采集器输出 ===")
    print(stdout)
    
    if stderr:
        print("\n=== DEBUG/错误输出 ===")
        print(stderr)
    
    # 验证输出中包含预期的指标
    expected_metrics = [
        'tgw,',
        'progVersion=',
        'latestGatewayVersion=',
        'gatewayType=',
        'certificationExpireTime=',
        'up=',
        'tgw_RunStatus,',
        'envId=',
        'commStatus=',
        'tgw_SessionStatus,',
        'sessionStatus=',
        'orderCount='
    ]
    
    print("\n=== 验证指标 ===")
    for metric in expected_metrics:
        if metric in stdout:
            print("✓ 找到指标: {}".format(metric))
        else:
            print("✗ 缺失指标: {}".format(metric))
    
    print("\n=== 测试完成 ===")
    
    # 清理临时文件
    if os.path.exists('test_integration_config.ini'):
        os.remove('test_integration_config.ini')
    
    # 停止服务器
    try:
        server_process.terminate()
        server_process.wait(timeout=2)
    except Exception as e:
        print("停止服务器异常: {}".format(e))

if __name__ == '__main__':
    """运行集成测试"""
    try:
        run_integration_test()
    except KeyboardInterrupt:
        print("测试被用户中断")
