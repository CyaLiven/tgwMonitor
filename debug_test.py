# -*- coding: utf-8 -*-
import subprocess
import sys
import time
import os

# 先确保配置文件存在
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

with open('test_debug_config.ini', 'w') as f:
    f.write(config_content)

# 先启动服务器
server = subprocess.Popen([sys.executable, 'mock_tgw_server.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(1)

# 再启动采集器
collector = subprocess.Popen(
    [sys.executable, 'tgwMonitor.py', '-c', 'test_debug_config.ini'], 
    stdout=subprocess.PIPE, 
    stderr=subprocess.PIPE
)
time.sleep(5)
collector.terminate()
stdout, stderr = collector.communicate(timeout=2)
server.terminate()

print('=== STDOUT ===')
print(stdout.decode('utf-8', errors='replace'))
print('=== STDERR ===')
print(stderr.decode('utf-8', errors='replace'))

# 清理
os.remove('test_debug_config.ini')
