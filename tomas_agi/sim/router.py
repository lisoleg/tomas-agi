"""
TOMAS LLM Router — 多模型路由引擎

核心理念（章锋 2026-06-15）：
  "TOMAS 从不绑定任何单一大模型。LLM 只是'外接皮层'与'舌头'，
   TOMAS 核心是'大脑与良知'（EML 超图 + NASGA + 死零/MUS）。
   十二家开源模型是十二种方言，TOMAS 是那个听懂方言并判真妄的耳朵。"

任务类型路由：
  reason       → DeepSeek (通用推理)        long_extract → GLM-5 (长文抽边)
  code_gen     → DeepSeek/Kimi (代码生成)    med_annotate → Miro-Med (医学标注)
  edu          → Gemma (教育/轻量)           academic     → InternLM (数理)
  rag          → Command-R (检索增强)        multilingual → Qwen3 (多语)
  fallback     → DeepSeek (兜底)

Author: Zhang Feng
Version: 2.0
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# 支持作为独立脚本或包模块导入
try:
    from .eml_injector import EMLInjector
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from eml_injector import EMLInjector

logger = logging.getLogger("tomas.router")


# ── 异常定义 ──

class RouterError(Exception):
    """Router 基础异常"""
    pass


class ModelNotAvailableError(RouterError):
    """模型不可用（未启用、未配置 API Key）"""
    pass


class RoutingError(RouterError):
    """路由失败"""
    pass


class LLMCallError(RouterError):
    """LLM API 调用失败"""
    pass


# ── 后端配置 ──

@dataclass
class ModelBackend:
    """单个 LLM 后端的配置"""
    name: str
    label: str
    provider: str
    model: str
    api_base: str
    api_key_env: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    enabled: bool = True
    notes: str = ""

    def get_api_key(self, override: Optional[str] = None) -> str:
        """获取 API Key，优先级：参数 > 环境变量 > '' """
        if override:
            return override
        return os.environ.get(self.api_key_env, "")

    @property
    def is_available(self) -> bool:
        """检查模型是否可用（启用且有 API Key）"""
        return self.enabled and bool(self.get_api_key())


# ── 路由器主体 ──

class TOMASRouter:
    """TOMAS 多模型路由器

    维护模型池，按 task_type 路由到对应后端，注入 EML 执行上下文。

    Usage:
        router = TOMASRouter()
        # 使用默认 DeepSeek
        answer = router.route("reason", "什么是量子纠缠？")

        # 指定任务类型
        answer = router.route("med_annotate", "心肾不交如何辨证？",
                              eml_ctx={"kappa": 4.0, "dead_zero_theta": 0.15})

        # 从配置文件加载
        router = TOMASRouter(config_path="model_pool.json")
    """

    # ── 默认配置 ──
    _DEFAULT_CONFIG_PATH = None  # 实现在 __init__ 中推断

    # ── 默认模型池（内置 3 个核心模型，其余从 JSON 加载）──
    _FALLBACK_BACKENDS: Dict[str, dict] = {
        "deepseek": {
            "name": "deepseek", "label": "DeepSeek V3",
            "provider": "DeepSeek AI", "model": "deepseek-chat",
            "api_base": "https://api.deepseek.com/v1",
            "api_key_env": "DEEPSEEK_API_KEY",
            "temperature": 0.7, "max_tokens": 4096, "timeout": 60,
            "enabled": True,
            "notes": "Built-in fallback — MoE 性价比之王"
        }
    }

    def __init__(self,
                 config_path: Optional[str] = None,
                 config_dict: Optional[dict] = None,
                 api_keys: Optional[Dict[str, str]] = None):
        """初始化 Router

        Args:
            config_path: model_pool.json 配置文件路径
            config_dict: 直接传入配置字典（优先级高于 config_path）
            api_keys: 手动传入的 API Key 字典 {"deepseek": "sk-xxx", ...}（最高优先级）
        """
        self.backends: Dict[str, ModelBackend] = {}
        self.routing_table: Dict[str, str] = {}
        self._api_keys: Dict[str, str] = api_keys or {}
        self.eml_injector = EMLInjector()
        self._config_path = config_path

        # 1. 加载配置文件或默认配置
        if config_dict:
            self._load_from_dict(config_dict)
        elif config_path and Path(config_path).exists():
            self._load_from_file(config_path)
        else:
            self._load_defaults()

        # 2. 注入手动 API Keys（最高优先级，覆盖环境变量）
        if api_keys:
            for name, key in api_keys.items():
                if name in self._api_keys:
                    self._api_keys[name] = key

        logger.info(f"[TOMAS Router] 初始化完成: {len(self._available_backends)}/{len(self.backends)} 模型可用")

    # ── 加载配置 ──

    def _load_from_file(self, path: str):
        """从 JSON 文件加载模型池配置"""
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
        self._load_from_dict(config)

    def _load_from_dict(self, config: dict):
        """从字典加载模型池配置"""
        # 解析 models
        models = config.get("models", {})
        for name, cfg in models.items():
            self.backends[name] = ModelBackend(
                name=cfg.get("name", name),
                label=cfg.get("label", cfg.get("provider", name)),
                provider=cfg.get("provider", "Unknown"),
                model=cfg.get("model", name),
                api_base=cfg.get("api_base", ""),
                api_key_env=cfg.get("api_key_env", f"{name.upper()}_API_KEY"),
                temperature=cfg.get("temperature", 0.7),
                max_tokens=cfg.get("max_tokens", 4096),
                timeout=cfg.get("timeout", 60),
                enabled=cfg.get("enabled", True),
                notes=cfg.get("notes", ""),
            )

        # 解析路由表
        routing = config.get("task_routing", {})
        for task_type, entry in routing.items():
            if isinstance(entry, dict):
                self.routing_table[task_type] = entry.get("default", "deepseek")
            else:
                self.routing_table[task_type] = entry

        # 确保 fallback 存在
        self.routing_table.setdefault("fallback", "deepseek")

        # EML 注入默认参数
        eml_cfg = config.get("eml_injection", {})
        if eml_cfg:
            self.eml_injector = EMLInjector(
                kappa=eml_cfg.get("kappa", 4.0),
                dead_zero_theta=eml_cfg.get("dead_zero_theta", 0.15),
                mus_tags=eml_cfg.get("mus_tags", ["Asym!=0 double-exist"]),
                kappa_snap_rule=eml_cfg.get("kappa_snap_rule"),
                arbitration_rule=eml_cfg.get("arbitration_rule"),
            )

    def _load_defaults(self):
        """加载内置默认配置（仅 DeepSeek）"""
        self._load_from_dict({"models": self._FALLBACK_BACKENDS, "task_routing": {
            "reason": {"default": "deepseek"},
            "code_gen": {"default": "deepseek"},
            "fallback": {"default": "deepseek"},
        }})

    # ── 属性 ──

    @property
    def _available_backends(self) -> Dict[str, ModelBackend]:
        """所有可用的后端（已启用 + 有 API Key）"""
        return {name: b for name, b in self.backends.items() if b.is_available}

    @property
    def available_models(self) -> List[dict]:
        """列出所有可用模型"""
        return [
            {"name": b.name, "label": b.label, "provider": b.provider,
             "model": b.model, "notes": b.notes}
            for b in self._available_backends.values()
        ]

    @property
    def all_models(self) -> List[dict]:
        """列出所有已注册模型（含未启用的）"""
        return [
            {"name": b.name, "label": b.label, "provider": b.provider,
             "model": b.model, "enabled": b.enabled, "notes": b.notes}
            for b in self.backends.values()
        ]

    @property
    def task_types(self) -> List[str]:
        """列出所有支持的任务类型"""
        return list(self.routing_table.keys())

    # ── 核心路由方法 ──

    def route(self,
              task_type: str,
              prompt: str,
              eml_ctx: Optional[dict] = None,
              sys_prompt: Optional[str] = None,
              concepts: Optional[List[dict]] = None,
              edges: Optional[List[dict]] = None,
              model_override: Optional[str] = None,
              temperature_override: Optional[float] = None) -> str:
        """按任务类型路由到对应模型并返回响应

        Args:
            task_type: 任务类型 (reason/long_extract/code_gen/med_annotate/...)
            prompt: 用户提示词
            eml_ctx: EML 执行上下文覆盖 {"kappa": 4.0, "dead_zero_theta": 0.15, "mus_tags": [...]}
            sys_prompt: 额外系统提示词（角色定义等）
            concepts: EML 匹配概念列表
            edges: EML 关联超边列表
            model_override: 强制指定模型名（跳过路由表）
            temperature_override: 覆盖温度参数

        Returns:
            LLM 响应文本

        Raises:
            ModelNotAvailableError: 目标模型不可用
            LLMCallError: API 调用失败
        """
        # 1. 选择后端
        if model_override:
            backend = self.backends.get(model_override)
            if not backend:
                raise ModelNotAvailableError(f"指定模型 '{model_override}' 不在模型池中")
        else:
            model_name = self.routing_table.get(task_type, self.routing_table["fallback"])
            backend = self.backends.get(model_name)
            if not backend:
                # fallback 到 deepseek
                backend = self.backends.get("deepseek")
                if not backend:
                    raise RoutingError("路由失败：无法找到任何可用后端")

        if not backend.is_available:
            raise ModelNotAvailableError(
                f"模型 '{backend.label}' ({backend.name}) 不可用。"
                f"请检查 {backend.api_key_env} 环境变量或启用状态。"
            )

        # 2. 解析 EML 上下文参数
        if eml_ctx:
            kappa = eml_ctx.get("kappa", self.eml_injector.ctx.kappa)
            theta = eml_ctx.get("dead_zero_theta", self.eml_injector.ctx.dead_zero_theta)
            mus_tags = eml_ctx.get("mus_tags", self.eml_injector.ctx.mus_tags)
            self.eml_injector.update_params(kappa=kappa, dead_zero_theta=theta, mus_tags=mus_tags)

        # 3. 构建消息（注入 EML 上下文）
        messages = self.eml_injector.wrap_query(
            query=prompt,
            concepts=concepts,
            edges=edges,
            base_sysprompt=sys_prompt,
        )

        # 4. 调用 LLM
        temperature = temperature_override if temperature_override is not None else backend.temperature

        start_time = time.time()
        try:
            logger.info(f"[TOMAS Router] task_type={task_type} → model={backend.label} ({backend.model})")
            print(f"[TOMAS Router] task_type={task_type} → model={backend.label} ({backend.model})")
            response = self._call_llm(backend, messages, temperature)
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"[TOMAS Router] 响应 {len(response)} 字符, {elapsed:.0f}ms")
            return response
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            raise LLMCallError(f"调用 {backend.label} 失败 ({elapsed:.0f}ms): {e}") from e

    def _call_llm(self, backend: ModelBackend, messages: List[dict],
                  temperature: Optional[float] = None) -> str:
        """通用 OpenAI 兼容 API 调用

        Args:
            backend: 模型后端配置
            messages: 消息列表
            temperature: 温度覆盖

        Returns:
            模型响应文本

        Raises:
            LLMCallError: 调用失败（含超时、认证失败、HTTP 错误）
        """
        api_key = self._api_keys.get(backend.name) or backend.get_api_key()
        if not api_key:
            raise ModelNotAvailableError(
                f"模型 '{backend.label}' 未配置 API Key。"
                f"请设置环境变量 {backend.api_key_env} 或通过 api_keys 参数传入。"
            )

        url = f"{backend.api_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": backend.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else backend.temperature,
            "max_tokens": backend.max_tokens,
            "stream": False,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=backend.timeout)
        except requests.exceptions.Timeout:
            raise LLMCallError(f"调用 {backend.label} 超时 ({backend.timeout}s)")
        except requests.exceptions.ConnectionError as e:
            raise LLMCallError(f"无法连接到 {backend.label} API: {e}")

        if resp.status_code == 401:
            raise LLMCallError(
                f"认证失败：{backend.label} ({backend.api_key_env})。请检查 API Key 是否正确。"
            )
        if resp.status_code == 429:
            raise LLMCallError(
                f"请求频率超限：{backend.label}。请稍后重试或切换模型。"
            )
        if not resp.ok:
            raise LLMCallError(
                f"{backend.label} 返回 HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except json.JSONDecodeError:
            raise LLMCallError(f"无法解析 {backend.label} 响应 JSON: {resp.text[:200]}")

        # 标准 OpenAI 响应格式
        choices = data.get("choices", [])
        if not choices:
            raise LLMCallError(f"{backend.label} 返回空 choices: {json.dumps(data, ensure_ascii=False)[:200]}")

        content = choices[0].get("message", {}).get("content", "")
        return content

    # ── 管理方法 ──

    def add_backend(self, name: str, backend_config: dict):
        """动态添加后端"""
        self.backends[name] = ModelBackend(
            name=name,
            label=backend_config.get("label", name),
            provider=backend_config.get("provider", "Unknown"),
            model=backend_config.get("model", name),
            api_base=backend_config.get("api_base", ""),
            api_key_env=backend_config.get("api_key_env", f"{name.upper()}_API_KEY"),
            temperature=backend_config.get("temperature", 0.7),
            max_tokens=backend_config.get("max_tokens", 4096),
            timeout=backend_config.get("timeout", 60),
            enabled=backend_config.get("enabled", True),
            notes=backend_config.get("notes", ""),
        )

    def set_route(self, task_type: str, model_name: str):
        """设置任务类型路由"""
        if model_name not in self.backends:
            raise RoutingError(f"模型 '{model_name}' 不在模型池中")
        self.routing_table[task_type] = model_name

    def enable_model(self, name: str):
        """启用指定模型"""
        if name in self.backends:
            self.backends[name].enabled = True

    def disable_model(self, name: str):
        """禁用指定模型"""
        if name in self.backends:
            self.backends[name].enabled = False

    def set_api_key(self, name: str, api_key: str):
        """手动设置 API Key"""
        self._api_keys[name] = api_key

    def to_dict(self) -> dict:
        """导出当前配置为字典"""
        return {
            "task_routing": dict(self.routing_table),
            "models": {
                name: {
                    "name": b.name,
                    "label": b.label,
                    "provider": b.provider,
                    "model": b.model,
                    "api_base": b.api_base,
                    "api_key_env": b.api_key_env,
                    "temperature": b.temperature,
                    "max_tokens": b.max_tokens,
                    "timeout": b.timeout,
                    "enabled": b.enabled,
                    "notes": b.notes,
                }
                for name, b in self.backends.items()
            },
        }


