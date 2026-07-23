# APIX 架构总结

```
Apix-Version_2.1/
│
├─ README.md                         # 项目说明（中英双语）
├─ setup.ps1 / setup.sh              # 一键安装脚本（Windows/macOS/Linux）
├─ start_all.bat                     # 开发环境一键启动
├─ embedEtcd.yaml                    # 内嵌 Etcd 配置
├─ user.yaml                         # 用户配置文件
│
├─ AGENT/                            # ★★★ Agent 核心服务（Python/FastAPI, Port 5091）
│   └─ agent_module/
│       ├─ main.py                   # ★ FastAPI 入口：lifespan 统一启动/关闭所有服务
│       │                            #   auto_load_router() → 扫描 routers/ 自动挂载
│       │                            #   event_handler_mgr.load_*() → 加载事件处理器
│       │                            #   auto_init.start() → 批量启动 5 个生命周期服务
│       │
│       ├─ apix_agent/
│       │   ├─ global_config.py      # ★ 全局配置：BASE_URL(8个厂商)、TTL、端口号
│       │   │
│       │   ├─ apix_agent_core/      # ★★★ Agent 引擎核心
│       │   │   ├─ agent.py          # ★★★ AgentRuningtime：后台 Worker 调度 + SubAgent 生命周期
│       │   │   │                    #   start() → 创建 worker-loop + stopper-loop 协程
│       │   │   │                    #   submit_agent_task() → 编译 StateGraph 返回给调用者
│       │   │   │                    #   _run_sub_agent() → 创建子Agent → astream → 追踪状态
│       │   │   │
│       │   │   ├─ generation_manager.py  # ★★ GenerationManager：每次 LLM 生成的生命周期
│       │   │   │                         #   create → running → update_cache_tokens
│       │   │   │                         #   → abort/finish → TTL 过期清理
│       │   │   │
│       │   │   ├─ agent_factory/
│       │   │   │   ├─ agent_creator.py   # ★★★ AgentCreator：LangGraph 图编译 + 缓存
│       │   │   │   │                    #   _create_agent_core() → 权限收集 → LLM创建
│       │   │   │   │                    #   → 工具获取 → add_node/add_edge → compile
│       │   │   │   │                    #   图缓存：hash_key → {graph, expire_at, status}
│       │   │   │   │
│       │   │   │   ├─ prompt.py         # ★ 所有 Prompt 模板（Leader/Agent/Worker/Summary/Tools）
│       │   │   │   │
│       │   │   │   └─ agent_node/
│       │   │   │       ├─ agent_node_base.py  # ★★ AgentNodeBase：4个抽象方法 + 路由逻辑
│       │   │   │       │                      #   should_continue() → tools/llm/END
│       │   │   │       │                      #   route_after_llm() → retry/summary/ok
│       │   │   │       │
│       │   │   │       ├─ main_agent_node.py  # ★★★ MainAgentNode：主Agent完整实现
│       │   │   │       │                      #   context_prepare → 沙箱/历史/技能/文档加载
│       │   │   │       │                      #   context_summary → 5级上下文压缩
│       │   │   │       │                      #   llm_call → Prompt组装 + 流式调用 + 异常重试
│       │   │   │       │                      #   messages_persist → 消息持久化到 Memory 服务
│       │   │   │       │
│       │   │   │       ├─ sub_agent_node.py   # ★★ SubAgentNode：子Agent实现
│       │   │   │       │                      #   消息走 generating_cache 不污染主对话
│       │   │   │       │                      #   支持 team_worker 模式（刷新共享历史）
│       │   │   │       │
│       │   │   │       └─ memory_agent_node.py # 记忆Agent节点（预留）
│       │   │   │
│       │   │   ├─ LLM/
│       │   │   │   ├─ llm_adapter.py     # ★★★ LlmNodeAdapter：统一流式/非流式接口
│       │   │   │   │                    #   astream() → 按 provider 适配 reasoning 参数
│       │   │   │   │                    #   ainvoke() → 非流式调用（摘要等场景）
│       │   │   │   │                    #   is_vision_model() → 探针检测视觉能力 + 缓存
│       │   │   │   │                    #   guess_exception_type() → token_exceed/rate_limit/others
│       │   │   │   │
│       │   │   │   ├─ llm_factory.py    # ★ LLM 实例工厂（支持 OpenAI/DeepSeek/Ollama 等）
│       │   │   │   └─ llm_creator.py    # LLM 创建器
│       │   │   │
│       │   │   ├─ tools/
│       │   │   │   ├─ __init__.py       # ★ 统一导出：20+ 工具函数汇聚到一个入口
│       │   │   │   ├─ registry.py       # ★★ 工具注册表：权限 → 工具列表映射
│       │   │   │   │                    #   get_available_tools() → 按权限过滤 + 去重
│       │   │   │   │                    #   conflict_tool_set → 冲突检测集合
│       │   │   │   │
│       │   │   │   ├─ tool_node.py      # ★ ApixToolNode：继承 LangGraph ToolNode
│       │   │   │   │                    #   _arun_one() → 异常捕获 → ToolMessage(status="error")
│       │   │   │   │
│       │   │   │   ├─ assistant/
│       │   │   │   │   └─ call_assistant.py  # ★★★ 多Agent协作工具
│       │   │   │   │                        #   assign_sub_assistant → 构建State → submit_task
│       │   │   │   │                        #   query_sub_assistant → 查询状态/todos/outputs
│       │   │   │   │                        #   stop_sub_assistant → 发送取消信号
│       │   │   │   │
│       │   │   │   ├─ basic_tools/
│       │   │   │   │   ├─ file_manager.py   # 文件CRUD工具
│       │   │   │   │   ├─ todo_list.py      # TODO + 记忆管理
│       │   │   │   │   ├─ skills.py         # 技能加载器
│       │   │   │   │   ├─ communication.py  # request_user_input（阻塞等待用户）
│       │   │   │   │   ├─ task_flow.py      # 自动化测试任务
│       │   │   │   │   └─ agent_ocr.py      # OCR + 图片发送
│       │   │   │   │
│       │   │   │   ├─ code_runner/
│       │   │   │   │   ├─ cmd.py            # Bash 命令执行
│       │   │   │   │   └─ python_code_runner.py  # Python 代码执行
│       │   │   │   │
│       │   │   │   ├─ web_search/           # Web搜索（DuckDuckGo/Bing/Google/Tavily/SearXNG）
│       │   │   │   ├─ vector_search/        # 知识库向量检索
│       │   │   │   └─ mcp/                  # MCP协议工具集成
│       │   │   │
│       │   │   ├─ context_manager/
│       │   │   │   ├─ context_process.py    # ★★★ AIContextManager：上下文全生命周期
│       │   │   │   │                        #   create_agent_messages() → Dict→LangChain对象
│       │   │   │   │                        #   create_dict_message() → LangChain→Dict
│       │   │   │   │                        #   drop_tool_messages() → 标记[outdated]
│       │   │   │   │                        #   split_messages() → 保护工具链边界的分割
│       │   │   │   │                        #   create_*_prompt() → 6种运行时Prompt
│       │   │   │   │
│       │   │   │   └─ generating_cache.py   # 子Agent消息缓存（独立于主对话）
│       │   │   │
│       │   │   ├─ sandbox_manager/
│       │   │   │   └─ agent_sandbox_manager.py  # ★★ Docker沙箱：容器池化 + TTL清理
│       │   │   │                               #   SHA256(client_id+work_dir) 键 + bind mount
│       │   │   │
│       │   │   └─ agent_task/
│       │   │       └─ team_task_manager.py   # ★★ TeamTaskManager：任务队列 + 状态机
│       │   │                                #   submit_task → task_queue.put()
│       │   │                                #   mark_in_progress/completed/failed/cancelled
│       │   │                                #   事件通知：post_event 驱动 handler
│       │   │
│       │   ├─ apix_event_pipe/          # ★★ 事件管道（双通道）
│       │   │   ├─ stream_event/
│       │   │   │   ├─ agent_stream_writer.py  # ★★ AgentStreamWriter：LangGraph内发送事件
│       │   │   │   │                          #   send_event() → 流式推送
│       │   │   │   │                          #   send_blocking_event() → Future等待用户响应
│       │   │   │   │                          #   resolve_block() → 前端回复后唤醒
│       │   │   │   │
│       │   │   │   └─ stream_event_gateway.py # ★★★ StreamEventHandler：处理chat/abort/await
│       │   │   │                              #   chat_with_llm() → 创建Generation → astream循环
│       │   │   │                              #   _ensure_config() → 配置合并 + 持久化缓存
│       │   │   │
│       │   │   ├─ common_event/
│       │   │   │   ├─ agent_event_writer.py   # ★ EventPipeWriter：asyncio.Queue生产者
│       │   │   │   ├─ common_event_gateway.py # ★★ PipeEventHandler：消费者 + dispatch
│       │   │   │   │                          #   信号量限流(Semaphore 100) + 超时保护
│       │   │   │   └─ event_registry.py       # ★★ EventRegistry：事件名→[HandlerEntry]
│       │   │   │                              #   @on_event 装饰器 + priority 排序
│       │   │   │
│       │   │   └─ event_handler_base.py       # ★ EventHandler 基类：build/send envelope
│       │   │
│       │   ├─ apix_event_handler/        # ★ 事件处理器注册
│       │   │   ├─ event_handler_manager.py    # ★ EventHandlerManager：启动时扫描加载
│       │   │   │                              #   load_system_handler() → import触发装饰器
│       │   │   │                              #   load_custom_handler() → 用户扩展入口
│       │   │   │
│       │   │   ├─ system_handler/
│       │   │   │   ├─ on_team_task.py         # ★★★ 子任务完成 → 心跳消息唤醒Leader
│       │   │   │   │                          #   feedback_to_agent() → 等待全部完成
│       │   │   │   │                          #   → 检查分支有效性 → chat_with_llm(心跳)
│       │   │   │   └─ on_cron_task.py         # 定时任务处理（预留）
│       │   │   │
│       │   │   └─ custom_handler/             # 用户自定义事件处理器目录
│       │   │
│       │   ├─ apix_platform/              # ★★ 平台抽象层
│       │   │   ├─ register.py                # ★ PLATFORM_REGISTRY 全局注册表
│       │   │   └─ platform/
│       │   │       ├─ platform_base.py       # ★ PlatformBase：send/trans_payload 接口
│       │   │       ├─ websocket_platform.py  # ★★ 每用户独立 Queue + sender_loop
│       │   │       ├─ default_platform.py    # ★ DefaultPlatform：注册为 platform="default"
│       │   │       └─ webhook_platform.py    # Webhook平台（HTTP POST回调）
│       │   │
│       │   ├─ apix_execution_context/    # ★ 执行上下文
│       │   │   ├─ execution_context_base.py  # ★★ ExecutionContextBase：分组管理 + 变更追踪
│       │   │   └─ agent_loop_context.py      # ★ AgentLoopContext：图外访问Agent状态
│       │   │                                  #   get_cached_message_chain() → Memory服务
│       │   │
│       │   ├─ commons/                   # 公共工具
│       │   │   ├─ auto_init.py              # ★★ AutoInit：服务定位器 + 生命周期容器
│       │   │   ├─ resource_cleaner.py       # ★★ ResourceCleaner：定时清理过期资源
│       │   │   ├─ type_def.py               # ★★★ 全部类型定义（异常/状态/配置/事件）
│       │   │   ├─ logger.py                 # 日志系统
│       │   │   ├─ decorator.py              # 装饰器工具
│       │   │   └─ common_func.py            # 通用函数
│       │   │
│       │   └─ routers/                  # API路由
│       │       ├─ websocket.py             # ★★ WebSocket入口：ws_endpoint()
│       │       │                           #   chat_with_llm → 异步任务启动
│       │       │                           #   abort_generation → 中断生成
│       │       │                           #   resolve_block → 回复阻塞事件
│       │       ├─ git.py                   # Git操作接口
│       │       ├─ infomation.py            # 服务信息接口
│       │       └─ settings.py              # 配置管理接口
│       │
│       └─ apix_running_time/           # 运行时数据目录
│           ├─ running_cache/            # 配置缓存 + memo
│           └─ AI_SERVER/                # 服务日志
│
├─ CLIENT/                            # ★★ 前端桌面客户端（Electron + Vue 3）
│   └─ apix-app/
│       ├─ package.json                # 依赖：Vue3.5 / Pinia / ElementPlus / CodeMirror
│       ├─ electron-builder.yml        # 打包配置（Win/Mac/Linux）
│       │
│       └─ src/
│           ├─ main/                   # ★ Electron 主进程
│           │   ├─ index.js            # 入口：createMainWindow + app事件
│           │   ├─ config.js           # API_BASE 配置
│           │   ├─ ws/wsClient.js      # ★★ WebSocket客户端：自动重连 + 指数退避
│           │   │                      #   wsSubscribers Map → 多渲染进程广播
│           │   ├─ ipc/
│           │   │   ├─ ai_chat.js      # ★★ 聊天IPC：chat/stop/new_chat/messages
│           │   │   ├─ ai_files.js     # 文件/技能/RAG 上传管理
│           │   │   ├─ ai_task.js      # 任务查询/终止
│           │   │   ├─ ai_configuration.js  # LLM/MCP 配置管理
│           │   │   └─ login_register.js    # 认证IPC
│           │   │
│           │   └─ modules/
│           │       └─ file_service/   # 本地文件系统监听（chokidar）
│           │
│           ├─ preload/index.js        # ★★ contextBridge：安全暴露 api.* 到渲染进程
│           │                          #   70+ IPC方法 + onWsMessage/onFsEvents 事件订阅
│           │
│           └─ renderer/src/           # ★ Vue 3 渲染进程
│               ├─ App.vue             # 根组件
│               ├─ main.js             # Vue入口 + Pinia + Router
│               ├─ LoginPage.vue       # 登录页
│               │
│               ├─ router/
│               │   ├─ index.js        # 路由守卫（auth）+ 动态路由注册
│               │   └─ pageRegistry.js # 可扩展的页面注册表
│               │
│               ├─ store/              # Pinia 状态管理
│               │   ├─ auth.js         # ★ 认证状态（localStorage持久化）
│               │   ├─ app.js          # 应用状态
│               │   └─ globalData.js   # 全局共享数据
│               │
│               └─ views/
│                   ├─ assistPage.vue       # ★★ 主聊天页面
│                   └─ component/
│                       ├─ msg_bubble_body/     # ★ 消息气泡（AI/Human/Tool/TODO）
│                       ├─ dialog_history/      # ★ 对话历史侧栏（分支切换）
│                       ├─ file_panel/          # 文件树浏览器
│                       ├─ code_edit/           # CodeMirror 代码编辑器
│                       ├─ mcp_card/            # MCP服务器管理
│                       └─ mini_chat/           # 小窗对话面板
│
├─ MEMORY/                            # ★ 记忆服务（Python/FastAPI, Port 5093）
│   └─ memory_module/
│       ├─ main.py                    # FastAPI入口：auto_load路由
│       └─ routers/
│           ├─ memory_record.py       # 对话消息CRUD + 短期记忆
│           └─ user_record.py         # 用户/对话管理
│
├─ FILE/                              # ★ 文件服务（Python/FastAPI, Port 5094）
│   └─ file_service/
│       ├─ main.py                    # FastAPI入口
│       └─ routers/
│           ├─ file_record.py         # 工作区文件管理
│           ├─ rag_record.py          # RAG知识库文档
│           ├─ skill_record.py        # 技能包管理
│           └─ information.py         # 服务信息
│
├─ TASK/                              # 任务流服务（Python/FastAPI, Port 5090）
│   └─ task_flow_module/
│       ├─ main.py                    # FastAPI入口
│       └─ app/routers/               # 任务队列 + 插件系统
│
└─ volumes/                           # 数据持久化卷
```

---

## 关键文件标注

| 重要性 | 文件 | 说明 |
|:------:|:-----|:------|
| ★★★ | `AGENT/.../agent_creator.py` | Agent 工厂：LangGraph 图编译 + hash 缓存 + 权限收集 + 工具绑定 |
| ★★★ | `AGENT/.../main_agent_node.py` | 主Agent节点：5级上下文压缩 + LLM调用 + 异常重试 + 消息持久化 |
| ★★★ | `AGENT/.../stream_event_gateway.py` | SSE流核心：chat_with_llm() 流式循环，配置合并，abort处理 |
| ★★★ | `AGENT/.../agent.py` | 运行时管理器：Worker 后台调度 + SubAgent 生命周期 + 异步任务追踪 |
| ★★★ | `AGENT/.../call_assistant.py` | 多Agent协作：派发/查询/停止 子Agent的3个工具 |
| ★★★ | `AGENT/.../type_def.py` | 全部类型定义：异常类 + State + Config + Event Envelope |
| ★★ | `AGENT/.../llm_adapter.py` | LLM适配器：统一 astream/ainvoke，DeepSeek/MoonShot reasoning 兼容 |
| ★★ | `AGENT/.../context_process.py` | 上下文管理器：Dict↔LangChain转换，6种Prompt构建，工具消息过滤 |
| ★★ | `AGENT/.../team_task_manager.py` | 团队任务管理器：asyncio.Queue 队列 + 任务状态机 + 事件通知 |
| ★★ | `AGENT/.../generation_manager.py` | 生成状态管理：running→finished/aborted + 缓存Token + TTL清理 |
| ★★ | `AGENT/.../agent_stream_writer.py` | 流事件写入器：send_event + send_blocking_event + Future 阻塞机制 |
| ★★ | `AGENT/.../common_event_gateway.py` | 通用事件网关：消费者循环 + dispatch 分发 + 信号量限流 |
| ★★ | `AGENT/.../event_registry.py` | 事件注册表：@on_event 装饰器 + priority 排序 + 责任链 |
| ★★ | `AGENT/.../agent_sandbox_manager.py` | Docker沙箱：容器池化 + bind mount + TTL过期清理 |
| ★★ | `AGENT/.../websocket_platform.py` | WebSocket平台：每用户独立 Queue + sender_loop 隔离 |
| ★★ | `AGENT/.../auto_init.py` | 自动初始化器：服务定位器模式 + 正向启动反向关闭 |
| ★★ | `AGENT/.../resource_cleaner.py` | 资源清理器：后台定时循环 + 装饰器自动注册 |
| ★★ | `AGENT/.../on_team_task.py` | 团队任务事件：子任务完成 → 心跳消息唤醒 Leader |
| ★★ | `CLIENT/.../wsClient.js` | WebSocket客户端：自动重连 + 指数退避 + 多订阅者广播 |
| ★ | `AGENT/main.py` | FastAPI入口：lifespan 统一管理所有服务生命周期 |
| ★ | `AGENT/.../global_config.py` | 全局配置：8个LLM厂商 BASE_URL + 超时 + TTL |
| ★ | `AGENT/.../registry.py` | 工具注册表：权限→工具映射 + 冲突集 + 子Agent禁用集 |
| ★ | `CLIENT/.../preload/index.js` | 预加载脚本：70+ IPC方法 + 事件订阅的安全桥接 |
| ★ | `CLIENT/.../ai_chat.js` | 聊天IPC：WebSocket消息发送 + HTTP回退（对话CRUD） |

---

## 数据流简图

### 用户发送消息 → Agent 回复

```
用户输入消息（Vue assistPage）
       │
       │ window.api.chatComplations(cid, sid, hid, msg, config)
       ▼
Electron IPC (ipcRenderer.invoke → ipcMain.handle)
       │
       │ ai_chat.js: ws.send({action: "chat_with_llm", data})
       ▼
AGENT WebSocket (websocket.py: ws_endpoint)
       │
       │ asyncio.create_task(action_handler.chat_with_llm(data))
       ▼
StreamEventHandler.chat_with_llm()
       │
       ├── generation_manager.create_generation()     ← 创建生成记录
       ├── _ensure_config()                            ← 合并/缓存配置
       ├── ai_agent.submit_agent_task()               ← 编译 LangGraph
       │     └── agent_creator.create_agent()
       │           ├── hash 缓存命中? → 直接返回
       │           └── 未命中 → LlmNodeAdapter + get_available_tools → compile
       │
       └── agent.astream(initial_state)               ← LangGraph 流式循环
             │
             ├── context_prepare  → 加载沙箱/历史/技能/文档/记忆
             ├── context_summary  → 按需 5级压缩
             ├── llm_call         → 构建Prompt + 流式调用LLM + 异常重试
             ├── messages_persist → 持久化到 Memory 服务
             ├── should_continue?
             │     ├── tools → ApixToolNode 执行 → 回到 messages_persist
             │     ├── llm   → 回到 context_summary
             │     └── END   → 结束
             │
             └── 每个节点内 AgentStreamWriter.send_event()
                   │
                   │ LangGraph stream_mode="custom"
                   ▼
             async for chunk in astream:
                 await _send_envelope(target, chunk)
                   │
                   │ PLATFORM_REGISTRY[platform].send()
                   ▼
             WebSocket → Electron Main → IPC → Vue 响应式渲染
```

### 多Agent协作流程

```
Main Agent (team_leader) 决定分配任务
       │
       │ tool_call: assign_sub_assistant(agent_identity, task_desc, instruction)
       ▼
call_assistant.assign_sub_assistant()
       │
       ├── 构建 SubAgentState（克隆父状态 + 重置 + history_id="sub_xxx"）
       └── team_task_manager.submit_task()
             └── task_queue.put((agent_name, initial_state, config))  ← 入队即返回
       │
Main Agent 收到 ToolMessage: "任务已分配" → 继续交互（不等待！）
       │
       │ ... 后台异步执行 ...
       ▼
AgentRuningtime._sub_agent_worker_loop()
       │
       └── task_queue.get() → asyncio.create_task(_run_sub_agent())
             │
             ├── mark_in_progress()    → post_event → 前端更新
             ├── create_sub_agent()    → 独立 LangGraph 编译
             ├── agent.astream()       → 子Agent独立运行
             ├── mark_completed()      → post_event("on_team_task_completed")
             └── _emit_generation_completed_if_needed()
                   │
                   │ 全部子任务完成?
                   └── post_event("on_generation_team_task_completed")
                         │
                         ▼
                   common_event_gateway dispatch
                         │
                         ▼
                   feedback_to_agent(event)  ← on_team_task.py
                         │
                         ├── await_for_generation()  → 等待活跃生成结束
                         ├── get_cached_message_chain() → 检查分支有效性
                         └── chat_with_llm(心跳消息)
                               │
                               ▼
                         Main Agent 收到心跳
                         → tool_call: query_sub_assistant(task_ids)
                         → 拿到结果 → 更新TODOs → 告知用户
```

---

## WebSocket 事件类型

### Agent → Client（流式推送）

| 事件名 | 触发时机 | 前端处理 |
|:-------|:---------|:---------|
| `msg_stream_start` | Agent 开始执行 | 创建新消息气泡，设置 node_id + parent_id |
| `node_stream_start` | 单次 LLM 调用开始 | 初始化流式内容缓存 |
| `think_chunk_rtn` | LLM 输出推理过程 | 追加到思考面板 |
| `content_chunk_rtn` | LLM 输出文本内容 | 流式追加到 AI 回答气泡 |
| `tool_chunk_rtn` | LLM 输出工具调用参数 | 在消息中展示工具调用信息 |
| `tool_exec_chunk_rtn` | 工具执行状态变化 | 工具标签卡（执行中/成功/失败） |
| `tool_exec_start/end` | 工具开始/结束执行 | chunk_position: start/end |
| `node_stream_end` | 单次 LLM 调用结束 | 完成本次流式渲染 |
| `msg_stream_end` | 整次生成结束 | 标记消息完成 |
| `msg_stream_abort` | 生成被中断 | 显示中断提示 + 保留已输出内容 |
| `parent_id_return` | 上下文准备完成 | 建立消息节点关系 |
| `runtime_warning` | 运行时警告 | 显示警告提示（token_limit/conflict_tools等） |
| `error_occurred` | 错误发生 | 错误提示 |

### Common Event（系统内部事件）

| 事件名 | 触发位置 | 处理者 |
|:-------|:---------|:-------|
| `on_team_task_task_submitted` | TeamTaskManager.submit_task() | 前端 UI 更新 |
| `on_team_task_in_progress` | TeamTaskManager.mark_in_progress() | 前端 UI 更新 |
| `on_team_task_completed` | TeamTaskManager.mark_completed() | feedback_to_agent |
| `on_team_task_failed` | TeamTaskManager.mark_failed() | feedback_to_agent |
| `on_team_task_cancelled` | TeamTaskManager.mark_cancelled() | feedback_to_agent |
| `on_generation_team_task_completed` | 全部子任务完成 | feedback_to_agent → 心跳唤醒Leader |
| `on_platform_registered` | 平台注册成功 | 日志记录 |

### Client → Agent（WebSocket 上行）

| action | 说明 |
|:-------|:-----|
| `chat_with_llm` | 发起 LLM 对话（异步任务，结果走流式推送） |
| `abort_generation` | 中断当前生成（触发 generation_manager.abort_by_history_id） |
| `resolve_block` | 回复阻塞事件（如 request_user_input 的用户回答） |

---

## 上下文压缩（5级渐进式）

| Level | 触发条件 | 策略 | 可逆 |
|:-----:|:---------|:-----|:----:|
| 0 | 消息量 < 阈值 | 无操作 | - |
| 1 | 消息量 ≥ 阈值 | 丢弃工具输出（标记 `[Tool Result Outdated]`） | ✅ |
| 2 | Level 1 不够 OR token_exceed | **LLM 摘要**：压缩早期消息 → 持久化 shortterm memory | ❌ |
| 3 | Level 2 不够 | 激进丢弃工具消息 (min_keep=2) | ✅ |
| 4+ | Level 3 不够 | 指数截断：`keep = base // 2^(level-3)`，最少保留 2 条 | ✅ |

---

## Agent 角色体系

| 角色 | 权限 | 上下文 | 适用场景 |
|:-----|:-----|:-------|:---------|
| `agent` | 全工具（除 sub_agent_assign） | 主对话 | 日常问答、代码编写 |
| `main_agent` | 全工具 + 分配 1 个子Agent | 主对话 | 需要委托的复杂任务 |
| `sub_agent` | 受限工具（无分配/通信权限） | 独立上下文 | 被 main_agent 委托执行 |
| `team_leader` | 全工具 + 分配多个子Agent | 主对话 | 大型多步骤项目 |
| `team_worker` | 受限工具 | 共享历史 (generating_cache) | 团队协作中的执行者 |

---

## 5个生命周期服务（auto_init 管理）

| 注册顺序 | 服务 | start() 行为 | stop() 行为 |
|:-------:|:-----|:------------|:-----------|
| 1 | `ai_agent` (AgentRuningtime) | 创建 worker-loop + stopper-loop 协程 | 取消两个协程 |
| 2 | `resource_cleaner` | 启动 300s 间隔的清理循环 | 取消清理循环 |
| 3 | `default_platform` | 为已连接用户启动 sender_loop | 取消所有 sender_loop |
| 4 | `agent_sandbox` | (空) | 停止所有 Docker 容器 |
| 5 | `mcp_mgr` | 初始化 MCP 客户端缓存 | 清理缓存 |
