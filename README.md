# 说明

* 基于公开文档进行编写：深圳证券市场接入服务网关监控接口规范，初次尝试vibe coding
* python版本需3.6.8或以上
* manage_tgwMonitor.sh和manage_tgwMonitor.sh可用于简单管理telegraf的execd
  * 将tgwMonitor.py或tgwMonitor_3.6.8.py、config.ini.template放置在目录/opt/scripts/telegraf/tgwMonitor
  * 建立telegraf配置目录/etc/telegraf/telegraf.d/tgw
* tgw_monitor_v0.1-Grafana.json导入后需要做修改
* rule.txt是一些简单的告警规则，可用作参考
