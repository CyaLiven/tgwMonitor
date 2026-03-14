# -*- coding: utf-8 -*-
import asyncio
import hashlib
import sys
import time
import configparser
import logging
import argparse
from pathlib import Path
from datetime import datetime

# 日志配置：输出到 stderr 避免干扰 Telegraf 的数据采集 (stdout)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TGWCollector:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.reader = None
        self.writer = None
        self.lock = asyncio.Lock()
        self.is_running = True
        self.auth_failed = False
        self.static_tags = {}
        self.static_metrics = {}
        self.load_config()

    def load_config(self):
        path = Path(self.config_path)
        if not path.exists():
            logger.error(f"配置文件不存在: {path}")
            sys.exit(1)
        
        cfg = configparser.ConfigParser()
        cfg.read(str(path), encoding='utf-8')
        try:
            self.host = cfg.get('gateway', 'host')
            self.port = cfg.getint('gateway', 'port')
            self.password = cfg.get('gateway', 'password')
            self.tgw_id_cfg = cfg.get('gateway', 'tgw_id')
            platforms_str = cfg.get('gateway', 'required_platforms', fallback='1,2,3,4,5,6')
            self.required_platforms = [p.strip() for p in platforms_str.split(',') if p.strip()]
            self.interval = cfg.getint('collector', 'interval')
            self.hb_interval = cfg.getint('collector', 'heartbeat_interval', fallback=20)
            self.static_status_interval = cfg.getint('collector', 'static_status_interval', fallback=300)
            self.timeout = cfg.getfloat('collector', 'timeout', fallback=5.0)
            self.retry_int = cfg.getint('collector', 'retry_interval', fallback=5)
            if cfg.getboolean('telegraf', 'debug', fallback=False):
                logger.setLevel(logging.DEBUG)
        except Exception as e:
            logger.error(f"配置文件解析错误: {e}")
            sys.exit(1)

    def _calc_password(self, salt: str) -> str:
        p1 = hashlib.sha256(self.password.encode()).hexdigest()
        return hashlib.sha256((salt + p1).encode()).hexdigest()

    def _date_to_timestamp(self, date_str: str) -> int:
        """YYYYMMDD 转 Unix 时间戳(秒)"""
        if not date_str or str(date_str) == "0":
            return 0
        try:
            dt = datetime.strptime(str(date_str), "%Y%m%d")
            return int(dt.timestamp())
        except Exception:
            return 0

    def _escape_tag_value(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        if not value:
            value = "na"
        return value.replace(',', '_').replace(' ', '_')

    def _format_line_protocol(self, measurement: str, tags: dict, fields: dict, use_static_tags: bool = True) -> str:
        """生成 InfluxDB Line Protocol"""
        all_tags = {**self.static_tags, **tags} if use_static_tags else tags.copy()
        if "tgw_id" not in all_tags:
            all_tags["tgw_id"] = self.tgw_id_cfg
            
        tag_str = ",".join([f"{k}={self._escape_tag_value(v)}" for k, v in all_tags.items()])
        field_list = []
        for k, v in fields.items():
            if isinstance(v, (int, float)):
                field_list.append(f"{k}={v}")
            else:
                v_esc = str(v).replace('"', '\\"')
                field_list.append(f'{k}="{v_esc}"')
        
        timestamp = time.time_ns()  # Python 3.7+ 原生纳秒时间戳
        return f"{measurement},{tag_str} {','.join(field_list)} {timestamp}"

    async def _request(self, msg_dict: dict) -> dict:
        """异步发送请求并解析响应为嵌套字典"""
        async with self.lock:
            payload = "\r\n".join([f"{k}={v}" for k, v in msg_dict.items()]) + "\r\n\r\n"
            self.writer.write(payload.encode('utf-8'))
            await self.writer.drain()
            
            lines = []
            while True:
                line_bytes = await asyncio.wait_for(self.reader.readuntil(b"\r\n"), timeout=self.timeout)
                line = line_bytes.decode('utf-8').strip()
                if not line: break
                lines.append(line)
            
            root = {}
            for line in lines:
                if '=' not in line: continue
                k_path, v = line.split('=', 1)
                parts = k_path.split('.')
                curr = root
                for i, p in enumerate(parts):
                    if i == len(parts) - 1:
                        curr[p] = v
                    else:
                        if p not in curr: curr[p] = {}
                        curr = curr[p]
            return root

    async def fetch_static_status(self):
        """解析 QueryStaticStatus：处理指标化版本信息"""
        try:
            res = await self._request({"type": "QueryStaticStatus"})
            if not res: return

            # 自动识别 GatewayID 字典
            actual_id = next((k for k, v in res.items() if isinstance(v, dict)), self.tgw_id_cfg)
            
            if actual_id != self.tgw_id_cfg:
                logger.error(f"匹配不一致！配置 tgw_id:[{self.tgw_id_cfg}], 网关返回:[{actual_id}]")

            info = res.get(actual_id, {})
            self.static_tags = {
                "tgw_id": actual_id,
                "osType": res.get("osType", "unknown")
            }

            self.static_metrics = {
                "progVersion": int(res.get("progVersion", "0")),
                "latestGatewayVersion": int(res.get("latestGatewayVersion", "0")),
                "gatewayType": int(info.get("gatewayType", 0)),
                "certificationExpireTime": self._date_to_timestamp(info.get("certificationExpireTime", "0"))
            }
            
        except Exception as e:
            logger.error(f"静态状态解析异常: {e}")

    async def heartbeat_loop(self):
        while True:
            try:
                await asyncio.sleep(self.hb_interval)
                await self._request({"type": "HeartBeat"})
            except Exception: break

    async def static_status_refresh_loop(self):
        while True:
            try:
                await asyncio.sleep(self.static_status_interval)
                if self.static_status_interval > 0:
                    await self.fetch_static_status()
            except Exception: break

    async def collect_task(self):
        """核心指标采集"""
        while True:
            try:
                print(self._format_line_protocol("tgw", {"tgw_host": self.host, "tgw_monitor_port": self.port}, {"up": 1}, use_static_tags=False))
                
                for key, value in self.static_metrics.items():
                    print(self._format_line_protocol("tgw", {}, {key: value}))
                
                for pid in self.required_platforms:
                    print(self._format_line_protocol("tgw_required", {"platform_id": pid}, {"platforms": 1}))
                
                actual_id = self.static_tags.get("tgw_id", self.tgw_id_cfg)

                # 1. QueryRunStatus 处理
                run_res = await self._request({"type": "QueryRunStatus"})
                if run_res.get('type') == 'RunStatus':
                    env_id = run_res.get('envId', '0')
                    gw_data = run_res.get(actual_id, {})
                    run_tags = {"serverAddress": gw_data.get('serverAddress', 'unknown')}
                    
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"envId": int(env_id)}))
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"commStatus": int(gw_data.get("commStatus", 0))}))
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"testMode": int(gw_data.get("testMode", 0))}))
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"orderRate": int(gw_data.get("orderRate", 0))}))
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"orderCount": int(gw_data.get("orderCount", 0))}))
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"orderConfirmCount": int(gw_data.get("orderConfirmCount", 0))}))
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"reportCount": int(gw_data.get("reportCount", 0))}))
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"invalidOrderCount": int(gw_data.get("invalidOrderCount", 0))}))
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"businessRejectCount": int(gw_data.get("businessRejectCount", 0))}))
                    
                    t_day = gw_data.get("tradeDay", "0")
                    print(self._format_line_protocol("tgw_RunStatus", run_tags, {"tradeDay": self._date_to_timestamp(t_day)}))

                    # 平台状态 1-6，未获取到的使用默认值 -99
                    existing_platforms = set(gw_data.get('platformState', {}).keys())
                    for pid in range(1, 7):
                        pval = gw_data.get('platformState', {}).get(str(pid), -99)
                        print(self._format_line_protocol("tgw_RunStatus", 
                              {**run_tags, "platform_id": str(pid)}, {"platformState": int(pval)}))

                # 2. QuerySessionStatus 处理
                sess_res = await self._request({"type": "QuerySessionStatus"})
                if sess_res.get('type') == 'SessionStatus':
                    sessions = sess_res.get(actual_id, {})
                    
                    platform_sessions = {}
                    for sid, sdata in sessions.items():
                        if isinstance(sdata, dict):
                            pid = sdata.get("platformId")
                            if pid:
                                platform_sessions[str(pid)] = sdata
                    
                    for pid in range(1, 7):
                        sdata = platform_sessions.get(str(pid))
                        if sdata:
                            stags = {
                                "platform_id": str(pid),
                                "compId": sdata.get("compId", "na"),
                                "peerAddress": sdata.get("peerAddress", "na")
                            }
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"sessionStatus": int(sdata.get("sessionStatus", -99))}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"orderCount": int(sdata.get("orderCount", 0))}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"orderConfirmCount": int(sdata.get("orderConfirmCount", 0))}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"reportCount": int(sdata.get("reportCount", 0))}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"invalidOrderCount": int(sdata.get("invalidOrderCount", 0))}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"businessRejectCount": int(sdata.get("businessRejectCount", 0))}))
                        else:
                            stags = {
                                "platform_id": str(pid),
                                "compId": "na",
                                "peerAddress": "na"
                            }
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"sessionStatus": -99}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"orderCount": 0}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"orderConfirmCount": 0}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"reportCount": 0}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"invalidOrderCount": 0}))
                            print(self._format_line_protocol("tgw_SessionStatus", stags, {"businessRejectCount": 0}))

                sys.stdout.flush()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"采集循环异常: {e}")
                raise

    async def run_forever(self):
        while self.is_running:
            if self.auth_failed:
                print(self._format_line_protocol("tgw", {"tgw_host": self.host, "tgw_monitor_port": self.port}, {"up": 0}, use_static_tags=False))
                sys.stdout.flush()
                await asyncio.sleep(self.interval)
                continue
            
            hb_task = None
            ss_task = None
            try:
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), timeout=self.timeout
                )
                
                # 握手鉴权
                salt_data = await self._request({"type": "QuerySalt"})
                login_res = await self._request({
                    "type": "Login", 
                    "password": self._calc_password(salt_data.get('salt', ''))
                })
                
                if login_res.get('loginStatus') != '1':
                    logger.error("鉴权失败")
                    self.auth_failed = True
                    if self.writer: self.writer.close()
                    continue
                
                await self.fetch_static_status()
                self.auth_failed = False
                
                hb_task = None
                ss_task = None
                # 开启心跳协程
                hb_task = asyncio.create_task(self.heartbeat_loop())
                if self.static_status_interval > 0:
                    ss_task = asyncio.create_task(self.static_status_refresh_loop())
                await self.collect_task()
                
            except Exception as e:
                if hb_task: hb_task.cancel()
                if ss_task: ss_task.cancel()
                logger.warning("连接异常: {} 目标地址: {}:{} tgw_id: {}".format(e, self.host, self.port, self.tgw_id_cfg))
                self.static_tags = {}
                self.static_metrics = {}
                print(self._format_line_protocol("tgw", {"tgw_host": self.host, "tgw_monitor_port": self.port}, {"up": -1}, use_static_tags=False))
                sys.stdout.flush()
                if self.writer: self.writer.close()
                await asyncio.sleep(self.retry_int)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.ini")
    args = parser.parse_args()
    
    try:
        asyncio.run(TGWCollector(args.config).run_forever())
    except KeyboardInterrupt:
        pass