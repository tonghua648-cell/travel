# Smart Travel｜AI 城市旅行助手 - 项目状态

## 当前定位

这是一个基于高德地图 Web 服务 API 的城市旅行助手 MVP。用户可以用两种方式生成方案：

- 手动模式：搜索并添加目的地，设置路线方式、评分权重和行程参数，然后计算酒店推荐和游览路线。
- Agent 模式：用户输入自然语言需求，例如旅游时长、同行老人小孩、交通便利偏好、想去的地点，系统自动解析需求、搜索目的地、推荐酒店并生成路线。

## 当前运行方式

```powershell
cd D:\CodexWorkspace\travel-assistant
python backend\server.py
```

打开：

```text
http://127.0.0.1:8000
```

高德 Key 读取顺序：

- 环境变量 `AMAP_KEY` 或 `GAODE_KEY`
- `backend/amap_key.txt`

OpenAI Key 是可选的：

- 环境变量 `OPENAI_API_KEY`
- `backend/openai_key.txt`

没有 OpenAI Key 时，Agent 会自动使用本地规则解析。

## 已实现功能

- 高德 POI 搜索目的地。
- 高德周边搜索酒店候选。
- 高德批量距离接口计算酒店到多个目的地的通勤成本。
- 酒店推荐排序：
  - 平均时间
  - 最远时间
  - 真实评分折算的舒适性，缺失时回退舒适性估计
  - 用户自定义权重
- 评分偏好预设：
  - 均衡
  - 时间优先
  - 舒适性优先
- 每个推荐酒店显示：
  - 平均时间
  - 最远时间
  - 舒适性分
  - 真实评分、参考价格和数据来源（当高德或本地数据提供时）
  - 性价比分和评分拆解
  - 驾车/公交均值
  - AI 推荐解读
  - 注意事项
- 页面入口：
  - 左侧 `酒店真实数据` 面板
  - 支持查看当前 `backend/hotel_data.json` 状态
  - 支持填入示例、粘贴 JSON 并保存本地酒店评分/价格数据
- 方案保存与分享：
  - 推荐结果可保存为短链接
  - 服务端写入 `backend/saved_plans.json`
  - 打开 `?plan=<id>` 可恢复目的地、推荐设置、推荐结果和已生成路线
- 酒店对比：
  - 最多选择 3 家酒店
  - 横向比较综合分、通勤、评分、参考价、性价比和数据来源
- 游览路线生成：
  - 从推荐酒店出发
  - 贪心排序目的地
  - 支持出发时间
  - 支持每个目的地停留时间
  - 支持是否返回酒店
  - 输出到达/离开时间、总通勤、总停留、预计结束时间
  - 地图绘制高德路线 polyline
- Agent 模式：
  - `POST /api/agent`
  - 自然语言解析城市、目的地、旅游时长、同行人、交通偏好
  - 自动调用搜索、推荐和路线生成
  - 有 OpenAI Key 时优先尝试 OpenAI Responses API 解析
  - 无 Key 或调用失败时回退本地规则解析

## 主要文件

- `backend/server.py`
  - Python 标准库 HTTP 服务
  - 高德 API 代理
  - 推荐算法
  - 行程算法
  - Agent 编排
- `backend/hotel_data.example.json`
  - 可选酒店评分/价格数据格式示例
  - 实际数据可放在 `backend/hotel_data.json`，或通过环境变量 `HOTEL_DATA_FILE` 指向
- `frontend/index.html`
  - Tailwind CDN 页面结构
  - Smart Travel UI
- `frontend/styles.css`
  - shadcn 风格卡片、控件、地图和结果样式
- `frontend/app.js`
  - 地图交互
  - 目的地搜索
  - 酒店推荐
  - 行程绘制
  - Agent 前端调用
- `.gitignore`
  - 忽略 `backend/amap_key.txt`
  - 忽略 `backend/openai_key.txt`

## 当前 API

### `GET /api/status`

返回高德 Key、OpenAI Key、默认城市、默认候选数量等状态。

### `GET /api/hotel-data`

返回本地酒店真实数据文件状态、路径、记录数量、当前内容和示例结构。

### `POST /api/hotel-data`

保存页面填写的酒店评分/价格 JSON 到 `backend/hotel_data.json`。

### `GET /api/plans?id=方案ID`

读取已保存的分享方案。

### `POST /api/plans`

保存当前页面方案快照，返回可分享的 `?plan=<id>` 链接。

### `GET /api/pois/search?q=关键词`

通过高德 POI 文本搜索返回目的地候选。

### `POST /api/recommend`

输入：

- `destinations`
- `routeMode`: `both | driving | transit`
- `preference`: `balanced | time | comfort`
- `weights`: `{ avgTime, maxTime, comfort }`
- `hotelLimit`

输出：

- `poiRecommendations`
- 每个酒店的时间、距离、舒适性、解释和推荐原因。

### `POST /api/itinerary`

输入：

- `origin`
- `destinations`
- `routeMode`
- `startTime`
- `stayMinutes`
- `returnToHotel`

输出：

- `orderedStops`
- `segments`
- `totalTravelMinutes`
- `totalStayMinutes`
- `endTime`
- 高德 polyline

### `POST /api/agent`

输入：

- `message`: 用户自然语言需求

输出：

- `parsed`
- `destinations`
- `recommendation`
- `itinerary`
- `message`
- `needsConfirmation`

## 已验证

### 2026-05-16 当前实现记录

- 已实现“酒店真实数据”页面入口：
  - 可在左侧面板查看 `backend/hotel_data.json` 状态。
  - 可填入示例、粘贴 JSON 并保存酒店评分/价格数据。
- 已实现“方案保存和分享链接”：
  - 推荐结果区域可点击 `保存方案`。
  - 后端写入 `backend/saved_plans.json`。
  - 返回 `?plan=<id>` 短链接。
  - 打开分享链接可恢复目的地、推荐设置、推荐结果和已生成路线。
- 已实现“酒店对比”：
  - 每张推荐酒店卡片可加入对比。
  - 最多同时对比 3 家酒店。
  - 横向展示综合分、平均时间、最远时间、评分、参考价、性价比和数据来源。
- 已实现价格/性价比评分：
  - 推荐结果新增 `valueScore`、`priceLevel`、`scoreBreakdown`。
  - 有价格时轻量影响最终排序。
  - 没有价格时保持原有排序，不强行惩罚。
- 当前服务已重启并运行在：

```text
http://127.0.0.1:8000
```

验证命令：

```powershell
python -m py_compile backend\server.py
node --check frontend\app.js
```

验证结果：

- 首页 `GET /` 返回 200。
- `GET /api/status` 返回 200。
- `POST /api/plans` 可保存方案。
- `GET /api/plans?id=<id>` 可读取方案。

示例请求：

```text
我在武汉有6小时，想去黄鹤楼、武汉大学和江汉路，带老人小孩，希望交通便利快速，帮我推荐酒店和游览路线。
```

本地规则 Agent 验证结果：

- 识别目的地：黄鹤楼、武汉大学、江汉路(地铁站)
- 推荐酒店：悦然居酒店(武汉昙华林店)
- 生成路线段数：4，包含返回酒店
- 预计结束时间：15:02

## 注意事项

- 高德免费 Key 可能触发 QPS 限制，候选酒店数建议先控制在 6-12。
- 公交 + 驾车择优会比只算驾车调用更多 API。
- 当前会优先使用高德 POI 扩展字段或 `backend/hotel_data.json` 中的真实评分/参考价格；只有缺失时才使用名称、类型、地址和电话做舒适性估计。
- 当前 Agent 的本地规则解析能识别常见武汉景点和常见偏好；更自然的开放表达建议配置 OpenAI Key。
- 当前路线排序是贪心策略，不是完整 TSP 全局最优。

## 建议下一步

- 进一步接入稳定 OTA/自有酒店库存 API，持续补全 `backend/hotel_data.json` 或通过 `HOTEL_DATA_FILE` 提供实时价格/评分。
- 增加“地铁少换乘”“少步行”“亲子友好”“老人友好”等显式偏好。（2026-05-16 已完成基础版）
- 增加方案保存和分享链接。（已实现本地短链版）
- 增加多日行程拆分。
- 如果使用 OpenAI Agent，后续可以升级为工具调用式多轮 Agent，而不是只做一次意图解析。

### 2026-05-16 继续开发记录

- 已新增显式出行偏好：
  - 少步行
  - 少换乘
  - 亲子友好
  - 老人友好
- 前端 `推荐设置` 中新增偏好开关，并纳入方案保存/恢复。
- 后端 `POST /api/recommend` 新增 `travelPreferences` 参数：
  - 启用偏好后会生成 `preferenceFitScore`
  - 公交详细线路可展示平均步行距离和平均换乘次数
  - 综合评分中会以较小权重纳入偏好匹配，保持与原有时间/舒适性评分兼容
- 后端 `POST /api/itinerary` 支持读取同一组 `travelPreferences`，公交路线会按偏好选择策略。
- Agent 规则解析和 OpenAI 解析 schema 已支持识别少步行、少换乘、亲子友好、老人友好。
- 当前服务已启动：`http://127.0.0.1:8000`
- 已验证：
  - `python -m py_compile backend\server.py`
  - `node --check frontend\app.js`
  - `GET /` 返回 200
  - `GET /api/status` 返回 200，且高德 Key 已配置
