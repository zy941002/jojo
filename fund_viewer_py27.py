#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金查看器 - Python 2.7兼容版本
在终端查看基金信息
作者: AI Assistant
功能: 查看基金实时数据、净值走势、基金详情等
"""

import requests
import json
import argparse
import sys
import re
from datetime import datetime, timedelta
import time

# Python 2.7兼容性处理
if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

# 颜色代码定义（不依赖colorama）
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class FundViewer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://fund.eastmoney.com/'
        })

    def get_fund_info(self, fund_code):
        """获取基金基本信息"""
        try:
            # 东方财富基金API
            url = "http://fundgz.1234567.com.cn/js/{}.js".format(fund_code)
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                # 提取JSON数据
                content = response.text
                json_match = re.search(r'jsonpgz\((.*?)\)', content)
                if json_match:
                    data = json.loads(json_match.group(1))
                    return data
            return None
        except Exception as e:
            print("{}获取基金 {} 信息失败: {}{}".format(Colors.RED, fund_code, e, Colors.END))
            return None

    def get_fund_detail(self, fund_code):
        """获取基金详细信息"""
        try:
            url = "http://api.fund.eastmoney.com/f10/jbgk/{}".format(fund_code)
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('Datas', {})
            return None
        except Exception as e:
            print("{}获取基金详细信息失败: {}{}".format(Colors.YELLOW, e, Colors.END))
            return None

    def search_fund(self, keyword):
        """搜索基金"""
        try:
            url = "http://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
            params = {
                'm': 1,
                'key': keyword,
                'type': 'all'
            }
            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('Datas', [])[:10]  # 只返回前10个结果
            return []
        except Exception as e:
            print("{}搜索基金失败: {}{}".format(Colors.RED, e, Colors.END))
            return []

    def format_fund_info(self, fund_data, detail_data=None):
        """格式化基金信息显示"""
        if not fund_data:
            return "{}无效的基金数据{}".format(Colors.RED, Colors.END)

        # 基本信息
        fund_code = fund_data.get('fundcode', 'N/A')
        fund_name = fund_data.get('name', 'N/A')
        net_value = fund_data.get('dwjz', 'N/A')
        estimate_value = fund_data.get('gsz', 'N/A')
        change_rate = fund_data.get('gszzl', 'N/A')
        update_time = fund_data.get('gztime', 'N/A')

        # 颜色设置
        if change_rate != 'N/A':
            try:
                rate_float = float(change_rate)
                if rate_float > 0:
                    rate_color = Colors.RED
                    rate_symbol = "+"
                elif rate_float < 0:
                    rate_color = Colors.GREEN
                    rate_symbol = ""
                else:
                    rate_color = Colors.WHITE
                    rate_symbol = ""
            except:
                rate_color = Colors.WHITE
                rate_symbol = ""
        else:
            rate_color = Colors.WHITE
            rate_symbol = ""

        # 构建显示内容
        result = """
{}{}
{}{}基金代码: {}{}
{}{}基金名称: {}{}
{}{}
{}最新净值: {}{}
{}估算净值: {}{}
{}涨跌幅度: {}{}{}%{}
{}更新时间: {}{}
""".format(
            Colors.CYAN, '='*60,
            Colors.YELLOW, Colors.BOLD, Colors.WHITE, fund_code,
            Colors.YELLOW, Colors.BOLD, Colors.WHITE, fund_name,
            Colors.CYAN, '='*60,
            Colors.BLUE, Colors.WHITE, net_value,
            Colors.BLUE, Colors.WHITE, estimate_value,
            Colors.BLUE, rate_color, rate_symbol, change_rate, Colors.END,
            Colors.BLUE, Colors.WHITE, update_time
        )

        # 添加详细信息
        if detail_data:
            fund_manager = detail_data.get('JJJL', 'N/A')
            fund_company = detail_data.get('JJGSMC', 'N/A')
            fund_type = detail_data.get('JJLX', 'N/A')
            establish_date = detail_data.get('CLRQ', 'N/A')
            fund_scale = detail_data.get('JJGM', 'N/A')

            result += """
{}{}
{}基金经理: {}{}
{}基金公司: {}{}
{}基金类型: {}{}
{}成立日期: {}{}
{}基金规模: {}{}
""".format(
                Colors.CYAN, '-'*60,
                Colors.MAGENTA, Colors.WHITE, fund_manager,
                Colors.MAGENTA, Colors.WHITE, fund_company,
                Colors.MAGENTA, Colors.WHITE, fund_type,
                Colors.MAGENTA, Colors.WHITE, establish_date,
                Colors.MAGENTA, Colors.WHITE, fund_scale
            )

        result += "{}{}{}".format(Colors.CYAN, '='*60, Colors.END)
        return result

    def display_search_results(self, results):
        """显示搜索结果"""
        if not results:
            print("{}未找到相关基金{}".format(Colors.YELLOW, Colors.END))
            return

        print("\n{}{}".format(Colors.CYAN, '='*80))
        print("{}{}搜索结果:{}".format(Colors.YELLOW, Colors.BOLD, Colors.END))
        print("{}{}".format(Colors.CYAN, '='*80))

        for i, fund in enumerate(results, 1):
            code = fund.get('CODE', 'N/A')
            name = fund.get('NAME', 'N/A')
            py = fund.get('PY', 'N/A')

            print("{}{:2d}. {}{} {}- {} {}({}){}".format(
                Colors.WHITE, i, Colors.GREEN, code,
                Colors.WHITE, name, Colors.YELLOW, py, Colors.END
            ))

        print("{}{}\n".format(Colors.CYAN, '='*80))

    def watch_fund(self, fund_codes, interval=30):
        """实时监控基金"""
        print("{}开始监控基金，刷新间隔: {}秒{}".format(Colors.YELLOW, interval, Colors.END))
        print("{}按 Ctrl+C 退出监控{}".format(Colors.YELLOW, Colors.END))

        try:
            while True:
                # 清屏
                import sys
                sys.stdout.write("\033[2J\033[H")
                sys.stdout.flush()

                print("{}{}基金实时监控 - {}{}".format(
                    Colors.CYAN, Colors.BOLD,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'), Colors.END
                ))
                print("{}{}".format(Colors.CYAN, '='*100))

                for fund_code in fund_codes:
                    fund_data = self.get_fund_info(fund_code)
                    if fund_data:
                        print(self.format_fund_info(fund_data))
                    else:
                        print("{}基金 {} 数据获取失败{}".format(Colors.RED, fund_code, Colors.END))

                print("{}下次刷新: {}秒后...{}".format(Colors.YELLOW, interval, Colors.END))
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n{}监控已停止{}".format(Colors.YELLOW, Colors.END))

def main():
    parser = argparse.ArgumentParser(description='基金查看器 - 在终端查看基金信息')
    parser.add_argument('codes', nargs='*', help='基金代码列表')
    parser.add_argument('-s', '--search', help='搜索基金')
    parser.add_argument('-d', '--detail', action='store_true', help='显示详细信息')
    parser.add_argument('-w', '--watch', action='store_true', help='实时监控模式')
    parser.add_argument('-i', '--interval', type=int, default=30, help='监控刷新间隔(秒)')

    args = parser.parse_args()

    viewer = FundViewer()

    # 搜索基金
    if args.search:
        results = viewer.search_fund(args.search)
        viewer.display_search_results(results)
        return

    # 检查是否提供了基金代码
    if not args.codes:
        print("{}使用示例:{}".format(Colors.YELLOW, Colors.END))
        print("{}  python fund_viewer_py27.py 000001 000300    # 查看基金{}".format(Colors.WHITE, Colors.END))
        print("{}  python fund_viewer_py27.py 000001 -d         # 查看详细信息{}".format(Colors.WHITE, Colors.END))
        print("{}  python fund_viewer_py27.py -s 华夏            # 搜索基金{}".format(Colors.WHITE, Colors.END))
        print("{}  python fund_viewer_py27.py 000001 -w          # 实时监控{}".format(Colors.WHITE, Colors.END))
        print("{}  python fund_viewer_py27.py 000001 -w -i 10    # 10秒刷新监控{}".format(Colors.WHITE, Colors.END))
        return

    # 实时监控模式
    if args.watch:
        viewer.watch_fund(args.codes, args.interval)
        return

    # 查看基金信息
    for fund_code in args.codes:
        print("{}正在获取基金 {} 的信息...{}".format(Colors.CYAN, fund_code, Colors.END))

        fund_data = viewer.get_fund_info(fund_code)
        detail_data = None

        if fund_data and args.detail:
            detail_data = viewer.get_fund_detail(fund_code)

        if fund_data:
            print(viewer.format_fund_info(fund_data, detail_data))
        else:
            print("{}基金代码 {} 无效或数据获取失败{}".format(Colors.RED, fund_code, Colors.END))

if __name__ == "__main__":
    main()



