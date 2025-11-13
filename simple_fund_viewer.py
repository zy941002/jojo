#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版基金查看器 - 兼容Python 2.7
不依赖外部库，使用内置urllib
"""

import json
import sys
import re
import argparse

# Python 2/3 兼容性
if sys.version_info[0] == 2:
    import urllib2 as urllib_request
    from urllib import quote
    reload(sys)
    sys.setdefaultencoding('utf-8')
else:
    import urllib.request as urllib_request
    from urllib.parse import quote

def get_fund_info(fund_code):
    """获取基金信息"""
    try:
        url = "http://fundgz.1234567.com.cn/js/{}.js".format(fund_code)

        # 创建请求
        request = urllib_request.Request(url)
        request.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

        # 发送请求
        response = urllib_request.urlopen(request, timeout=10)
        content = response.read()

        if sys.version_info[0] == 3:
            content = content.decode('utf-8')

        # 提取JSON数据
        json_match = re.search(r'jsonpgz\((.*?)\)', content)
        if json_match:
            data = json.loads(json_match.group(1))
            return data
        return None

    except Exception as e:
        print("获取基金 {} 信息失败: {}".format(fund_code, e))
        return None

def format_fund_info(fund_data):
    """格式化基金信息"""
    if not fund_data:
        return "无效的基金数据"

    fund_code = fund_data.get('fundcode', 'N/A')
    fund_name = fund_data.get('name', 'N/A')
    net_value = fund_data.get('dwjz', 'N/A')
    estimate_value = fund_data.get('gsz', 'N/A')
    change_rate = fund_data.get('gszzl', 'N/A')
    update_time = fund_data.get('gztime', 'N/A')

    # 简单的涨跌标识
    if change_rate != 'N/A':
        try:
            rate_float = float(change_rate)
            if rate_float > 0:
                rate_str = "+{}% ↑".format(change_rate)
            elif rate_float < 0:
                rate_str = "{}% ↓".format(change_rate)
            else:
                rate_str = "{}% →".format(change_rate)
        except:
            rate_str = "{}%".format(change_rate)
    else:
        rate_str = "N/A"

    # 处理中文编码
    if sys.version_info[0] == 2:
        if isinstance(fund_name, str):
            fund_name = fund_name.decode('utf-8')

    result = u"""
============================================================
基金代码: {}
基金名称: {}
============================================================
最新净值: {}
估算净值: {}
涨跌幅度: {}
更新时间: {}
============================================================
""".format(fund_code, fund_name, net_value, estimate_value, rate_str, update_time)

    if sys.version_info[0] == 2:
        result = result.encode('utf-8')

    return result

def main():
    parser = argparse.ArgumentParser(description='简化版基金查看器')
    parser.add_argument('codes', nargs='*', help='基金代码列表')

    args = parser.parse_args()

    if not args.codes:
        print("使用示例:")
        print("  python simple_fund_viewer.py 000001")
        print("  python simple_fund_viewer.py 000001 000300")
        print("\n常用基金代码:")
        print("  000001 - 华夏成长混合")
        print("  000300 - 华夏沪深300ETF联接A")
        print("  161725 - 招商中证白酒指数分级")
        print("  110003 - 易方达上证50指数A")
        return

    for fund_code in args.codes:
        print("正在获取基金 {} 的信息...".format(fund_code))
        fund_data = get_fund_info(fund_code)

        if fund_data:
            print(format_fund_info(fund_data))
        else:
            print("基金代码 {} 无效或数据获取失败\n".format(fund_code))

if __name__ == "__main__":
    main()
