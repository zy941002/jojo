#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金查看器 - 在终端查看基金信息
作者: AI Assistant
功能: 查看基金实时数据、净值走势、基金详情等
"""

import requests
import json
import argparse
import sys
from datetime import datetime, timedelta
import re
from colorama import init, Fore, Back, Style
import time
import unicodedata

# 兼容不同Python版本
try:
    from typing import Dict, List, Optional
except ImportError:
    # Python 3.5以下版本不支持typing
    Dict = dict
    List = list
    Optional = None

# 初始化colorama，支持彩色输出
init(autoreset=True)

class FundViewer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://fund.eastmoney.com/'
        })
        self.history_cache: Dict[str, List[Dict]] = {}
        self.enable_backtest: bool = True
        self.backtest_days: int = 60

    def get_fund_info(self, fund_code: str) -> Optional[Dict]:
        """获取基金基本信息"""
        try:
            # 东方财富基金API
            url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
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
            print(f"{Fore.RED}获取基金 {fund_code} 信息失败: {e}")
            return None

    def get_fund_detail(self, fund_code: str) -> Optional[Dict]:
        """获取基金详细信息"""
        try:
            url = f"http://api.fund.eastmoney.com/f10/jbgk/{fund_code}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('Datas', {})
            return None
        except Exception as e:
            print(f"{Fore.YELLOW}获取基金详细信息失败: {e}")
            return None

    def get_fund_history(self, fund_code: str, days: int = 120) -> List[Dict]:
        """获取近N日历史净值（按日期升序）。返回: [{date: 'YYYY-MM-DD', nav: float}]"""
        try:
            cache_key = f"{fund_code}:{days}"
            if cache_key in self.history_cache:
                return self.history_cache[cache_key]

            # 东方财富 历史净值 API（返回HTML片段）
            # 说明：page=1 通常为最近数据；per 指定返回条数
            url = "http://fund.eastmoney.com/f10/F10DataApi.aspx"
            params = {
                'type': 'lsjz',
                'code': fund_code,
                'page': 1,
                'per': max(30, days + 10),
            }
            headers = {
                'Referer': f'http://fundf10.eastmoney.com/',
                'User-Agent': self.session.headers['User-Agent'],
            }
            resp = self.session.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200:
                return []

            text = resp.text
            # 提取 content:"..." 中的HTML
            m = re.search(r'content:\s*"(.*)"\s*,\s*records:', text)
            if not m:
                return []
            html = m.group(1)
            # 还原转义字符
            html = html.replace('\\/','/').replace('\\"','"').replace("\\n", "")

            # 解析 <tr> 行
            rows = []
            for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', html, flags=re.I|re.S):
                tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, flags=re.I|re.S)
                if len(tds) < 2:
                    continue
                date_str = re.sub(r'<[^>]*>', '', tds[0]).strip()
                nav_str = re.sub(r'<[^>]*>', '', tds[1]).strip()
                try:
                    nav_val = float(nav_str)
                except Exception:
                    continue
                rows.append({'date': date_str, 'nav': nav_val})

            # 页面为倒序（新->旧），转换为升序
            rows.reverse()
            if days and len(rows) > days:
                rows = rows[-days:]

            self.history_cache[cache_key] = rows
            return rows
        except Exception:
            return []

    def _compute_ma(self, series: List[float], window: int, idx: int) -> Optional[float]:
        if idx + 1 < window:
            return None
        s = series[idx - window + 1: idx + 1]
        return sum(s) / float(window)

    def compute_simple_backtest(self, fund_code: str, days: int = 60, short_window: int = 5, long_window: int = 10) -> Optional[str]:
        """简易MA5/MA10金叉策略回测摘要。返回字符串。"""
        hist = self.get_fund_history(fund_code, max(days, long_window + 5))
        if len(hist) < long_window + 2:
            return None
        navs = [h['nav'] for h in hist]
        n = len(navs)
        start_idx = max(1, n - days)

        capital = 1.0
        wins = 0
        trades = 0
        position_prev = 0

        for i in range(start_idx, n):
            ma_s = self._compute_ma(navs, short_window, i - 1)
            ma_l = self._compute_ma(navs, long_window, i - 1)
            if ma_s is None or ma_l is None:
                continue
            position = 1 if ma_s > ma_l else 0
            r = navs[i] / navs[i - 1] - 1.0
            if position_prev == 1:
                capital *= (1.0 + r)
                trades += 1
                if r > 0:
                    wins += 1
            position_prev = position

        bh = navs[-1] / navs[start_idx] - 1.0 if navs[start_idx] > 0 else 0.0
        strat = capital - 1.0
        win_rate = (wins / trades * 100.0) if trades > 0 else 0.0

        # 当前信号状态
        ma_s_now = self._compute_ma(navs, short_window, n - 1)
        ma_l_now = self._compute_ma(navs, long_window, n - 1)
        status = "持有" if (ma_s_now is not None and ma_l_now is not None and ma_s_now > ma_l_now) else "观望"

        return f"MA5/10近{min(days, n-1)}日:{strat:+.1f}% 胜:{win_rate:.0f}% BH:{bh:+.1f}% {status}"

    def search_fund(self, keyword: str) -> List[Dict]:
        """搜索基金"""
        try:
            url = f"http://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
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
            print(f"{Fore.RED}搜索基金失败: {e}")
            return []

    def format_fund_info(self, fund_data: Dict, detail_data: Optional[Dict] = None) -> str:
        """格式化基金信息显示"""
        if not fund_data:
            return f"{Fore.RED}无效的基金数据"

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
                    rate_color = Fore.RED
                    rate_symbol = "+"
                elif rate_float < 0:
                    rate_color = Fore.GREEN
                    rate_symbol = ""
                else:
                    rate_color = Fore.WHITE
                    rate_symbol = ""
            except:
                rate_color = Fore.WHITE
                rate_symbol = ""
        else:
            rate_color = Fore.WHITE
            rate_symbol = ""

        # 构建显示内容
        result = f"""
{Fore.CYAN}{'='*60}
{Fore.YELLOW}{Style.BRIGHT}基金代码: {Fore.WHITE}{fund_code}
{Fore.YELLOW}{Style.BRIGHT}基金名称: {Fore.WHITE}{fund_name}
{Fore.CYAN}{'='*60}
{Fore.BLUE}最新净值: {Fore.WHITE}{net_value}
{Fore.BLUE}估算净值: {Fore.WHITE}{estimate_value}
{Fore.BLUE}涨跌幅度: {rate_color}{rate_symbol}{change_rate}%
{Fore.BLUE}更新时间: {Fore.WHITE}{update_time}
"""

        # 添加详细信息
        if detail_data:
            fund_manager = detail_data.get('JJJL', 'N/A')
            fund_company = detail_data.get('JJGSMC', 'N/A')
            fund_type = detail_data.get('JJLX', 'N/A')
            establish_date = detail_data.get('CLRQ', 'N/A')
            fund_scale = detail_data.get('JJGM', 'N/A')

            result += f"""
{Fore.CYAN}{'-'*60}
{Fore.MAGENTA}基金经理: {Fore.WHITE}{fund_manager}
{Fore.MAGENTA}基金公司: {Fore.WHITE}{fund_company}
{Fore.MAGENTA}基金类型: {Fore.WHITE}{fund_type}
{Fore.MAGENTA}成立日期: {Fore.WHITE}{establish_date}
{Fore.MAGENTA}基金规模: {Fore.WHITE}{fund_scale}
"""

        result += f"{Fore.CYAN}{'='*60}\n"
        return result

    def display_search_results(self, results: List[Dict]) -> None:
        """显示搜索结果"""
        if not results:
            print(f"{Fore.YELLOW}未找到相关基金")
            return

        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}搜索结果:")
        print(f"{Fore.CYAN}{'='*80}")

        for i, fund in enumerate(results, 1):
            code = fund.get('CODE', 'N/A')
            name = fund.get('NAME', 'N/A')
            py = fund.get('PY', 'N/A')

            print(f"{Fore.WHITE}{i:2d}. {Fore.GREEN}{code} {Fore.WHITE}- {name} {Fore.YELLOW}({py})")

        print(f"{Fore.CYAN}{'='*80}\n")

    def _visual_width(self, text: str) -> int:
        """计算终端显示宽度（考虑ANSI颜色与中日韩宽字符）。"""
        s = self._strip_ansi(text)
        width = 0
        for ch in s:
            # 跳过组合字符
            if unicodedata.combining(ch):
                continue
            eaw = unicodedata.east_asian_width(ch)
            width += 2 if eaw in ('W', 'F') else 1
        return width

    def _pad_display(self, text: str, target_width: int) -> str:
        pad = target_width - self._visual_width(text)
        return text + (' ' * pad if pad > 0 else '')

    def _strip_ansi(self, text: str) -> str:
        try:
            return re.sub(r'\x1b\[[0-9;]*m', '', str(text))
        except Exception:
            return str(text)

    def _build_row(self, fund_data: Dict, detail_data: Optional[Dict] = None, include_backtest: bool = False, backtest_days: int = 60) -> Dict:
        fund_code = fund_data.get('fundcode', 'N/A')
        fund_name = fund_data.get('name', 'N/A')
        net_value = fund_data.get('dwjz', 'N/A')
        estimate_value = fund_data.get('gsz', 'N/A')
        change_rate = fund_data.get('gszzl', 'N/A')
        update_time = fund_data.get('gztime', 'N/A')

        # 颜色设置
        rate_display = change_rate
        if change_rate != 'N/A':
            try:
                rate_float = float(change_rate)
                if rate_float > 0:
                    rate_color = Fore.RED
                    rate_symbol = "+"
                elif rate_float < 0:
                    rate_color = Fore.GREEN
                    rate_symbol = ""
                else:
                    rate_color = Fore.WHITE
                    rate_symbol = ""
                rate_display = f"{rate_color}{rate_symbol}{change_rate}%"
            except:
                rate_display = f"{change_rate}%"
        else:
            rate_display = change_rate

        row = {
            '代码': fund_code,
            '名称': fund_name,
            '净值': net_value,
            '估值': estimate_value,
            '涨跌幅': rate_display,
            '更新时间': update_time,
        }

        if detail_data:
            row['类型'] = detail_data.get('JJLX', 'N/A')

        if include_backtest and fund_code and fund_code != 'N/A':
            try:
                summary = self.compute_simple_backtest(fund_code, days=backtest_days)
                row['简单策略回测'] = summary if summary else 'N/A'
            except Exception:
                row['简单策略回测'] = 'N/A'

        return row

    def format_table(self, rows: List[Dict], headers: List[str]) -> str:
        if not rows:
            return f"{Fore.YELLOW}无数据"

        # 计算每列宽度（忽略ANSI颜色并考虑宽字符）
        widths: List[int] = []
        for h in headers:
            max_len = self._visual_width(h)
            for r in rows:
                max_len = max(max_len, self._visual_width(r.get(h, '')))
            widths.append(max_len)

        # 构建表格
        parts = []
        # 表头（高亮）
        colored_headers = [f"{Style.BRIGHT}{Fore.CYAN}{h}{Style.RESET_ALL}" for h in headers]
        # 特别突出“涨跌幅”表头
        if '涨跌幅' in headers:
            idx = headers.index('涨跌幅')
            colored_headers[idx] = f"{Style.BRIGHT}{Fore.YELLOW}{headers[idx]}{Style.RESET_ALL}"
        header_line = " | ".join(self._pad_display(colored_headers[i], widths[i]) for i in range(len(headers)))
        sep_line = f"{Fore.CYAN}" + "=+=".join('=' * widths[i] for i in range(len(headers))) + f"{Style.RESET_ALL}"
        parts.append(header_line)
        parts.append(sep_line)
        # 数据行
        rate_idx = headers.index('涨跌幅') if '涨跌幅' in headers else -1
        for r in rows:
            line_cells = []
            for i, h in enumerate(headers):
                cell = str(r.get(h, ''))
                # 对“涨跌幅”整列使用黄色文字，不使用背景色，并统一覆盖内部颜色
                if i == rate_idx:
                    plain = self._strip_ansi(cell)
                    colored = f"{Fore.YELLOW}{plain}{Style.RESET_ALL}"
                    padded = self._pad_display(colored, widths[i])
                else:
                    padded = self._pad_display(cell, widths[i])
                line_cells.append(padded)
            parts.append(" | ".join(line_cells))

        return "\n".join(parts)

    def watch_fund(self, fund_codes: List[str], interval: int = 30) -> None:
        """实时监控基金"""
        print(f"{Fore.YELLOW}开始监控基金，刷新间隔: {interval}秒")
        print(f"{Fore.YELLOW}按 Ctrl+C 退出监控")

        try:
            while True:
                # 清屏
                print("\033[2J\033[H", end="")

                print(f"{Fore.CYAN}{Style.BRIGHT}基金实时监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{Fore.CYAN}{'='*100}")

                rows: List[Dict] = []
                for fund_code in fund_codes:
                    fund_data = self.get_fund_info(fund_code)
                    if fund_data:
                        rows.append(self._build_row(fund_data, include_backtest=self.enable_backtest, backtest_days=self.backtest_days))
                    else:
                        rows.append({
                            '代码': fund_code,
                            '名称': f"{Fore.RED}获取失败",
                            '净值': 'N/A',
                            '估值': 'N/A',
                            '涨跌幅': 'N/A',
                            '更新时间': '-',
                        })

                headers = ['代码', '名称', '净值', '估值', '涨跌幅', '更新时间']
                if any('简单策略回测' in r for r in rows):
                    headers.append('简单策略回测')
                print(self.format_table(rows, headers))

                print(f"{Fore.YELLOW}下次刷新: {interval}秒后...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}监控已停止")

def main():
    parser = argparse.ArgumentParser(description='基金查看器 - 在终端查看基金信息')
    parser.add_argument('codes', nargs='*', help='基金代码列表')
    parser.add_argument('-s', '--search', help='搜索基金')
    parser.add_argument('-d', '--detail', action='store_true', help='显示详细信息')
    parser.add_argument('-w', '--watch', action='store_true', help='实时监控模式')
    parser.add_argument('-i', '--interval', type=int, default=30, help='监控刷新间隔(秒)')
    parser.add_argument('-t', '--table', action='store_true', help='表格形式展示结果')
    parser.add_argument('--no-backtest', action='store_true', help='禁用简单策略回测列')
    parser.add_argument('--bt-days', type=int, default=60, help='回测区间天数，默认60')

    args = parser.parse_args()

    viewer = FundViewer()
    viewer.enable_backtest = not args.no_backtest
    viewer.backtest_days = max(20, args.bt_days)

    # 搜索基金
    if args.search:
        results = viewer.search_fund(args.search)
        viewer.display_search_results(results)
        return

    # 检查是否提供了基金代码
    if not args.codes:
        print(f"{Fore.YELLOW}使用示例:")
        print(f"{Fore.WHITE}  python fund_viewer.py 000001 000300    # 查看基金")
        print(f"{Fore.WHITE}  python fund_viewer.py 000001 -d         # 查看详细信息")
        print(f"{Fore.WHITE}  python fund_viewer.py -s 华夏            # 搜索基金")
        print(f"{Fore.WHITE}  python fund_viewer.py 000001 -w          # 实时监控")
        print(f"{Fore.WHITE}  python fund_viewer.py 000001 -w -i 10    # 10秒刷新监控")
        print(f"{Fore.WHITE}  python fund_viewer.py 000001 -t          # 表格展示")
        print(f"{Fore.WHITE}  python fund_viewer.py 000001 -t --bt-days 90   # 表格+90日回测")
        return

    # 实时监控模式
    if args.watch:
        viewer.watch_fund(args.codes, args.interval)
        return

    # 查看基金信息
    if args.table or len(args.codes) > 1:
        rows: List[Dict] = []
        for fund_code in args.codes:
            print(f"{Fore.CYAN}正在获取基金 {fund_code} 的信息...")
            fund_data = viewer.get_fund_info(fund_code)
            detail_data = None
            if fund_data and args.detail:
                detail_data = viewer.get_fund_detail(fund_code)
            if fund_data:
                rows.append(viewer._build_row(fund_data, detail_data, include_backtest=viewer.enable_backtest, backtest_days=viewer.backtest_days))
            else:
                rows.append({
                    '代码': fund_code,
                    '名称': f"{Fore.RED}获取失败",
                    '净值': 'N/A',
                    '估值': 'N/A',
                    '涨跌幅': 'N/A',
                    '更新时间': '-',
                })
        headers = ['代码', '名称', '净值', '估值', '涨跌幅', '更新时间']
        if any('类型' in r for r in rows):
            headers.append('类型')
        if any('简单策略回测' in r for r in rows):
            headers.append('简单策略回测')
        print(viewer.format_table(rows, headers))
    else:
        for fund_code in args.codes:
            print(f"{Fore.CYAN}正在获取基金 {fund_code} 的信息...")

            fund_data = viewer.get_fund_info(fund_code)
            detail_data = None

            if fund_data and args.detail:
                detail_data = viewer.get_fund_detail(fund_code)

            if fund_data:
                print(viewer.format_fund_info(fund_data, detail_data))
            else:
                print(f"{Fore.RED}基金代码 {fund_code} 无效或数据获取失败")

if __name__ == "__main__":
    main()
