# -*- coding: utf-8 -*-
"""
TGW 网关模拟服务器
用于测试 TGWCollector 的连接、认证和数据采集功能
"""

import asyncio
import hashlib

class MockTGWServer:
    """模拟 TGW 网关服务器"""
    
    def __init__(self, host='127.0.0.1', port=7000):
        """初始化模拟服务器
        
        Args:
            host (str): 服务器主机地址
            port (int): 服务器端口
        """
        self.host = host
        self.port = port
        self.server = None
        self.clients = []
        self.salt = 'test_salt_123456'
        self.expected_password = 'your_password'  # 预期密码，与config.ini一致
    
    async def handle_client(self, reader, writer):
        """处理客户端连接
        
        Args:
            reader: 读取器
            writer: 写入器
        """
        client_addr = writer.get_extra_info('peername')
        print(f'[MockTGWServer] 客户端连接: {client_addr}')
        self.clients.append(writer)
        
        try:
            while True:
                # 读取请求
                data = await reader.readuntil(b'\r\n\r\n')
                if not data:
                    break
                
                # 解析请求
                request = data.decode('utf-8')
                print(f'[MockTGWServer] 收到请求:\n{request}')
                
                # 处理请求
                response = await self.process_request(request)
                
                # 发送响应
                writer.write(response.encode('utf-8'))
                await writer.drain()
                
        except Exception as e:
            print(f'[MockTGWServer] 客户端处理异常: {e}')
        finally:
            print(f'[MockTGWServer] 客户端断开: {client_addr}')
            if writer in self.clients:
                self.clients.remove(writer)
            writer.close()
            await writer.wait_closed()
    
    async def process_request(self, request):
        """处理请求并生成响应
        
        Args:
            request (str): 请求内容
            
        Returns:
            str: 响应内容
        """
        lines = request.strip().split('\r\n')
        request_data = {}
        
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                request_data[key] = value
        
        request_type = request_data.get('type')
        print(f"[MockTGWServer] 处理请求类型: {request_type}")
        
        if request_type == 'QuerySalt':
            response = f'salt={self.salt}\r\n\r\n'
            print(f"[MockTGWServer] 发送响应: {response}")
            return response
        
        elif request_type == 'Login':
            password = request_data.get('password')
            # 验证密码
            expected_hash = self._calc_expected_hash()
            print(f"[MockTGWServer] 收到登录密码: {password}")
            print(f"[MockTGWServer] 预期密码哈希: {expected_hash}")
            if password == expected_hash:
                response = 'loginStatus=1\r\n\r\n'
            else:
                response = 'loginStatus=0\r\n\r\n'
            print(f"[MockTGWServer] 发送响应: {response}")
            return response
        
        elif request_type == 'QueryStaticStatus':
            response = (
                'type=StaticStatus\r\n'
                'progVersion=20150118\r\n'
                'latestGatewayVersion=20150423\r\n'
                'osType=Linux\r\n'
                'osVersion=Red Hat Enterprise Linux Server 7.5 (Maipo)\r\n'
                'W123456Y0001.gatewayType=1\r\n'
                'W123456Y0001.certification=TestKey1\r\n'
                'W123456Y0001.pbuId=000100\r\n'
                'W123456Y0001.pbuId=000200\r\n'
                'W123456Y0001.pbuId=000300\r\n'
                '\r\n'
            )
            print(f"[MockTGWServer] 发送响应: {response}")
            return response
        
        elif request_type == 'QueryRunStatus':
            response = (
                'type=RunStatus\r\n'
                'envId=0\r\n'
                'W123456Y0001.commStatus=1\r\n'
                'W123456Y0001.testMode=0\r\n'
                'W123456Y0001.tradeDay=20140619\r\n'
                'W123456Y0001.orderRate=50\r\n'
                'W123456Y0001.gatewayId=W123456Y0001\r\n'
                'W123456Y0001.serverAddress=192.168.0.1\r\n'
                'W123456Y0001.platformState.1=2\r\n'
                'W123456Y0001.platformState.2=2\r\n'
                'W123456Y0001.platformState.3=2\r\n'
                'W123456Y0001.platformState.4=2\r\n'
                'W123456Y0001.orderCount=1000\r\n'
                'W123456Y0001.orderConfirmCount=1000\r\n'
                'W123456Y0001.reportCount=1500\r\n'
                'W123456Y0001.invalidOrderCount=100\r\n'
                'W123456Y0001.businessRejectCount=100\r\n'
                'W123456Y0001.lastDisconnectReason=Connect refused\r\n'
                '\r\n'
            )
            print(f"[MockTGWServer] 发送响应: {response}")
            return response
        
        elif request_type == 'QuerySessionStatus':
            response = (
                'type=SessionStatus\r\n'
                'W123456Y0001.0.sessionStatus=1\r\n'
                'W123456Y0001.0.peerAddress=127.0.0.1:12345\r\n'
                'W123456Y0001.0.compId=CompId\r\n'
                'W123456Y0001.0.platformId=1\r\n'
                'W123456Y0001.0.orderCount=1000\r\n'
                'W123456Y0001.0.orderConfirmCount=1000\r\n'
                'W123456Y0001.0.reportCount=1500\r\n'
                'W123456Y0001.0.invalidOrderCount=100\r\n'
                'W123456Y0001.0.businessRejectCount=100\r\n'
                'W123456Y0001.1.sessionStatus=1\r\n'
                'W123456Y0001.1.peerAddress=127.0.0.1:12345\r\n'
                'W123456Y0001.1.compId=CompId\r\n'
                'W123456Y0001.1.platformId=2\r\n'
                'W123456Y0001.1.orderCount=1000\r\n'
                'W123456Y0001.1.orderConfirmCount=1000\r\n'
                'W123456Y0001.1.reportCount=1500\r\n'
                'W123456Y0001.1.invalidOrderCount=100\r\n'
                'W123456Y0001.1.businessRejectCount=100\r\n'
                'W123456Y0001.1.partition.1.expectReportIndex=1500\r\n'
                'W123456Y0001.1.partition.2.expectReportIndex=1210\r\n'
                'W123456Y0001.1.partition.3.expectReportIndex=983\r\n'
                'W123456Y0001.1.partition.4.expectReportIndex=1619\r\n'
                '\r\n'
            )
            print(f"[MockTGWServer] 发送响应: {response}")
            return response
        
        elif request_type == 'HeartBeat':
            response = '\r\n'
            print(f"[MockTGWServer] 发送响应: {response}")
            return response
        
        else:
            response = 'error=unknown_command\r\n\r\n'
            print(f"[MockTGWServer] 发送响应: {response}")
            return response
    
    def _calc_expected_hash(self):
        """计算预期的密码哈希值
        
        Returns:
            str: 计算后的哈希值
        """
        p1 = hashlib.sha256(self.expected_password.encode()).hexdigest()
        return hashlib.sha256((self.salt + p1).encode()).hexdigest()
    
    async def start(self):
        """启动服务器"""
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        addr = self.server.sockets[0].getsockname()
        print(f'[MockTGWServer] 服务器启动: {addr}')
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """停止服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print('[MockTGWServer] 服务器停止')

if __name__ == '__main__':
    """运行模拟服务器"""
    server = MockTGWServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print('[MockTGWServer] 服务器被用户中断')
