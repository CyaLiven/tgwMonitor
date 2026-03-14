# -*- coding: utf-8 -*-
"""
测试运行脚本
用于运行所有测试
"""

import os
import sys
import subprocess

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_unit_tests():
    """运行单元测试"""
    print("=== 运行单元测试 ===")
    result = subprocess.run([sys.executable, '-m', 'unittest', 'test_tgw_collector.py'], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("错误:", result.stderr)
    print(f"单元测试结果: {'通过' if result.returncode == 0 else '失败'}")
    print()

def run_integration_test():
    """运行集成测试"""
    print("=== 运行集成测试 ===")
    result = subprocess.run([sys.executable, 'integration_test.py'], 
                          capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("错误:", result.stderr)
    print(f"集成测试结果: {'通过' if result.returncode == 0 else '失败'}")
    print()

def run_mock_server():
    """运行模拟服务器"""
    print("=== 运行模拟TGW服务器 ===")
    print("服务器将在新窗口中启动，按 Ctrl+C 停止")
    print()
    if os.name == 'nt':  # Windows
        subprocess.Popen(['start', 'cmd', '/k', f'{sys.executable} mock_tgw_server.py'], shell=True)
    else:  # Linux/Mac
        subprocess.Popen(['xterm', '-e', f'{sys.executable} mock_tgw_server.py'])

def main():
    """主函数"""
    print("TGWCollector 测试套件")
    print("=" * 50)
    
    while True:
        print("\n请选择要运行的测试:")
        print("1. 运行单元测试")
        print("2. 运行集成测试")
        print("3. 启动模拟TGW服务器")
        print("4. 退出")
        
        choice = input("请输入选项 (1-4): ")
        
        if choice == '1':
            run_unit_tests()
        elif choice == '2':
            run_integration_test()
        elif choice == '3':
            run_mock_server()
        elif choice == '4':
            print("退出测试套件")
            break
        else:
            print("无效选项，请重新输入")

if __name__ == '__main__':
    main()
