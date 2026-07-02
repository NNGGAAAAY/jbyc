# 生产部署脚本

## 文件说明

- `start-prod.ps1`
  - 一键生产启动
  - 自动执行 `subst X:`、前端构建、后端启动、Nginx 启动
- `start-backend.ps1`
  - 单独启动 FastAPI 后端
- `start-nginx.ps1`
  - 单独启动或重载 Nginx
- `issue-ssl.ps1`
  - 自动下载 `win-acme`
  - 用 `http-01 + filesystem` 为 `ojxdxcx.xyz` / `www.ojxdxcx.xyz` 申请 PEM 证书
  - 自动写入 `nginx-1.30.0/conf/ssl-enabled/ojxdxcx.xyz.conf`
  - 自动重载 Nginx

## 启动前条件

1. 域名 `ojxdxcx.xyz` 和 `www.ojxdxcx.xyz` 的 `A` 记录必须指向当前机器公网 IP
2. 路由器或云防火墙必须放通：
   - `80`
   - `443`
3. Windows 防火墙必须放通：
   - `80`
   - `443`
4. MySQL 服务 `MySQL97Trae` 可启动

## 一键生产启动

在 PowerShell 里执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prod\start-prod.ps1
```

如果只想启动，不重新构建前端：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prod\start-prod.ps1 -SkipBuild
```

## 申请 HTTPS 证书

在 PowerShell 里执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prod\issue-ssl.ps1 -EmailAddress your@email.com
```

脚本会自动：

1. 检查域名解析是否已指向当前机器
2. 构建前端
3. 启动后端和 Nginx
4. 下载 `win-acme`
5. 申请证书并保存到：

```text
X:\nginx-1.30.0\conf\certs
```

6. 自动重载 Nginx，使 `https://ojxdxcx.xyz` 生效

## 当前 Nginx 证书接入路径

- 证书链：

```text
X:\nginx-1.30.0\conf\certs\ojxdxcx.xyz-chain.pem
```

- 私钥：

```text
X:\nginx-1.30.0\conf\certs\ojxdxcx.xyz-key.pem
```
