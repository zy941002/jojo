const http = require('http');
const https = require('https');
const url = require('url');
const path = require('path');
const fs = require('fs');

const PORT = 9988;

// MIME类型映射
const mimeTypes = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.wav': 'audio/wav',
    '.mp4': 'video/mp4',
    '.woff': 'application/font-woff',
    '.ttf': 'application/font-ttf',
    '.eot': 'application/vnd.ms-fontobject',
    '.otf': 'application/font-otf',
    '.wasm': 'application/wasm'
};

// 设置CORS头
function setCORSHeaders(res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    res.setHeader('Access-Control-Allow-Credentials', 'true');
}

// 代理请求到基金API
function proxyRequest(req, res, targetUrl) {
    const options = {
        hostname: url.parse(targetUrl).hostname,
        port: url.parse(targetUrl).port || (targetUrl.startsWith('https') ? 443 : 80),
        path: url.parse(targetUrl).path,
        method: req.method,
        headers: {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'http://fund.eastmoney.com/',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache'
        }
    };

    const protocol = targetUrl.startsWith('https') ? https : http;

    const proxyReq = protocol.request(options, (proxyRes) => {
        setCORSHeaders(res);
        res.writeHead(proxyRes.statusCode, proxyRes.headers);
        proxyRes.pipe(res);
    });

    proxyReq.on('error', (err) => {
        console.error('代理请求错误:', err);
        setCORSHeaders(res);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: '代理请求失败', message: err.message }));
    });

    req.pipe(proxyReq);
}

// 服务静态文件
function serveStaticFile(req, res, filePath) {
    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.writeHead(404, { 'Content-Type': 'text/plain' });
            res.end('File not found');
            return;
        }

        const ext = path.extname(filePath);
        const mimeType = mimeTypes[ext] || 'text/plain';

        setCORSHeaders(res);
        res.writeHead(200, { 'Content-Type': mimeType });
        res.end(data);
    });
}

// 创建HTTP服务器
const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    const pathname = parsedUrl.pathname;

    console.log(`${new Date().toISOString()} - ${req.method} ${pathname}`);

    // 处理OPTIONS预检请求
    if (req.method === 'OPTIONS') {
        setCORSHeaders(res);
        res.writeHead(200);
        res.end();
        return;
    }

    // 代理基金API请求
    if (pathname.startsWith('/api/fund/history/')) {
        const segments = pathname.split('/');
        const fundCode = segments.pop() || segments.pop();
        if (fundCode && /^\d{6}$/.test(fundCode)) {
            const days = parseInt(parsedUrl.query.days, 10);
            const pageSize = Number.isFinite(days) && days > 0 ? Math.min(Math.max(days, 60), 365) : 120;
            const targetUrl = `https://fundmobapi.eastmoney.com/FundMNewApi/FundMNHisNetList?` +
                `FCODE=${fundCode}&pageIndex=1&pageSize=${pageSize}&appType=ttjj&product=EFund&plat=Iphone&version=6.3.8&deviceid=00000000-0000-0000-0000-000000000000`;
            proxyRequest(req, res, targetUrl);
            return;
        }
    } else if (pathname.startsWith('/api/fund/')) {
        const fundCode = pathname.split('/').pop();
        if (fundCode && /^\d{6}$/.test(fundCode)) {
            const targetUrl = `https://fundgz.1234567.com.cn/js/${fundCode}.js`;
            proxyRequest(req, res, targetUrl);
            return;
        }
    }

    // 服务静态文件
    let filePath = path.join(__dirname, pathname === '/' ? 'fund_calculator.html' : pathname);

    // 检查文件是否存在
    fs.access(filePath, fs.constants.F_OK, (err) => {
        if (err) {
            // 如果文件不存在，尝试添加.html扩展名
            if (!path.extname(filePath)) {
                filePath += '.html';
                fs.access(filePath, fs.constants.F_OK, (err) => {
                    if (err) {
                        res.writeHead(404, { 'Content-Type': 'text/plain' });
                        res.end('File not found');
                    } else {
                        serveStaticFile(req, res, filePath);
                    }
                });
            } else {
                res.writeHead(404, { 'Content-Type': 'text/plain' });
                res.end('File not found');
            }
        } else {
            serveStaticFile(req, res, filePath);
        }
    });
});

// 启动服务器 - 监听所有网络接口，允许公网访问
const HOST = '0.0.0.0';
server.listen(PORT, HOST, () => {
    console.log('🚀 代理服务器启动成功！');
    console.log(`📡 本地地址: http://localhost:${PORT}`);
    console.log(`🌐 公网地址: http://<服务器IP>:${PORT}`);
    console.log(`📊 基金计算器: http://<服务器IP>:${PORT}/fund_calculator.html`);
    console.log(`🔗 API代理: http://<服务器IP>:${PORT}/api/fund/{基金代码}`);
    console.log('');
    console.log('💡 使用说明:');
    console.log('   - 服务器已监听所有网络接口 (0.0.0.0)');
    console.log('   - 确保防火墙已开放端口 ' + PORT);
    console.log('   - 云服务器请检查安全组规则');
    console.log('   - 按 Ctrl+C 停止服务器');
    console.log('');
});

// 优雅关闭
process.on('SIGINT', () => {
    console.log('\n🛑 正在关闭服务器...');
    server.close(() => {
        console.log('✅ 服务器已关闭');
        process.exit(0);
    });
});

// 错误处理
server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        console.error(`❌ 端口 ${PORT} 已被占用，请尝试其他端口或关闭占用该端口的程序`);
    } else {
        console.error('❌ 服务器错误:', err);
    }
    process.exit(1);
});

module.exports = server;
