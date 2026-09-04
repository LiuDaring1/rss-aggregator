# upstream-custom/ — 对上游引擎的自研贡献与本机适配

本目录的文件不属于上游原样，是本项目自研/修改的部分。上游引擎本体（RSSHub、we-mp-rss）为第三方开源项目，不整包入库，按各 README 安装。

## rsshub-routes/ → 拷入 RSSHub `lib/routes/` 对应位置

| 本目录文件 | 放置到 | 说明 |
| ---- | ---- | ---- |
| `zjol_zjxc.ts` | `lib/routes/zjol/zjxc.ts` | 浙江宣传（列表+详情） |
| `thepaper_studio.ts` | `lib/routes/thepaper/studio.ts` | 澎湃·工作室（studio_20=马上评），走官方 API |
| `gmw_namespace.ts` | `lib/routes/gmw/namespace.ts` | 光明网 namespace（上游无此目录） |
| `gmw_guancha.ts` | `lib/routes/gmw/guancha.ts` | 光明网评论频道栏目 |
| `rednet_namespace.ts` | `lib/routes/rednet/namespace.ts` | 红网 namespace（上游无此目录） |
| `rednet_channel.ts` | `lib/routes/rednet/channel.ts` | 红网红辣椒评论栏目，兼容新旧模板 |
| `youth_namespace.ts` | `lib/routes/youth/namespace.ts` | 中青 namespace（上游无此目录） |
| `youth_pinglun.ts` | `lib/routes/youth/pinglun.ts` | 中青评论频道，GBK 解码 |
| `bjnews_kuaiping.ts` | `lib/routes/bjnews/kuaiping.ts` | 新京报快评·风向标（自研路由，源站 WAF 对策） |
| `bjnews_utils_PATCHED.ts` | `lib/routes/bjnews/utils.ts` | **本地补丁**：详情页请求加完整浏览器头（2026-09 源站阿里云 WAF 会 405 头部不全的请求） |

注意：`lib/routes/zjol/namespace.ts`、`lib/routes/thepaper/` 其余文件为上游已有，不要覆盖。

## we-mp-rss/ → 拷入 we-mp-rss 根目录

| 本目录文件 | 说明 |
| ---- | ---- |
| `requirements-314.txt` | Python 3.14 适配依赖清单（放开 pydantic/pillow/greenlet 版本锁，去 psycopg2） |
| `start-local.sh` | 本机启动脚本：默认账号 admin/admin@123（环境变量可覆盖），启动时清空代理环境变量强制直连 |

`config.yaml` 从 `config.example.yaml` 复制后本地填写（含微信授权状态的数据目录 `data/` 不入库、不入包）。
