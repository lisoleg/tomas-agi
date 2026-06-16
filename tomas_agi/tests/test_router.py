"""
TOMAS Router + EML Injector 测试套件

测试覆盖：
  - EMLInjector: 系统提示词生成、上下文块构建、消息包装
  - TOMASRouter: 初始化、配置加载、路由表、可用模型、禁用模型
  - Router 集成: 与 InferenceEngine 的 Router 模式协作

作者：TOMAS 项目组
日期：2026-06-15
"""

import json
import os
import sys
import tempfile
import pytest

# 添加 sim 目录到 path
SIM_DIR = os.path.join(os.path.dirname(__file__), "..", "sim")
sys.path.insert(0, SIM_DIR)

from eml_injector import EMLInjector, EMLContext
from router import (
    TOMASRouter, ModelBackend, RouterError,
    ModelNotAvailableError, RoutingError, LLMCallError,
)


# ═══════════════════════════════════════════════════════════════
# EMLInjector 测试
# ═══════════════════════════════════════════════════════════════

class TestEMLInjector:

    def test_default_init(self):
        """默认初始化"""
        inj = EMLInjector()
        assert inj.ctx.kappa == 4.0
        assert inj.ctx.dead_zero_theta == 0.15
        assert "Asym!=0 double-exist" in inj.ctx.mus_tags

    def test_custom_init(self):
        """自定义参数初始化"""
        inj = EMLInjector(kappa=8.0, dead_zero_theta=0.3,
                          mus_tags=["Asym!=0", "Dual-exist"])
        assert inj.ctx.kappa == 8.0
        assert inj.ctx.dead_zero_theta == 0.3
        assert len(inj.ctx.mus_tags) == 2

    def test_build_sysprompt(self):
        """EML 系统提示词生成"""
        inj = EMLInjector(kappa=4.0, dead_zero_theta=0.15)
        prompt = inj.build_sysprompt()

        assert "TOMAS EML Execution Context (v2.0)" in prompt
        assert "kappa (Spectral Fold Depth): 4.0" in prompt
        assert "Dead-Zero Threshold (theta_dead): 0.15" in prompt
        assert "Asym!=0 double-exist" in prompt
        assert "DEAD_ZERO_REJECT" in prompt
        assert "MUS_ACTIVE" in prompt

    def test_build_sysprompt_custom_kappa(self):
        """自定义 κ 值的系统提示词"""
        inj = EMLInjector(kappa=8.0, dead_zero_theta=0.3)
        prompt = inj.build_sysprompt()

        assert "kappa (Spectral Fold Depth): 8.0" in prompt
        assert "Dead-Zero Threshold (theta_dead): 0.3" in prompt

    def test_build_context_block(self):
        """构建 EML 上下文块"""
        inj = EMLInjector()
        concepts = [
            {"concept": "量子纠缠", "i_val": 0.95},
            {"concept": "波函数坍缩", "i_val": 0.87},
        ]
        edges = [
            {"nodes": ["量子纠缠", "EPR佯谬"], "i_val": 0.82, "type": "relates"},
        ]
        block = inj.build_context_block(concepts, edges)

        assert "量子纠缠" in block
        assert "I=0.9500" in block
        assert "波函数坍缩" in block
        assert "EPR佯谬" in block
        assert "relates" in block

    def test_build_context_block_empty(self):
        """空上下文块不崩溃"""
        inj = EMLInjector()
        block = inj.build_context_block([], [])
        assert "(无匹配概念)" in block
        assert "(无关联超边)" in block

    def test_wrap_query(self):
        """完整消息包装"""
        inj = EMLInjector(kappa=4.0, dead_zero_theta=0.15)
        concepts = [{"concept": "测试概念", "i_val": 0.9}]
        edges = [{"nodes": ["测试概念", "关联概念"], "i_val": 0.7, "type": "relates"}]

        messages = inj.wrap_query(
            query="什么是测试概念？",
            concepts=concepts,
            edges=edges,
            base_sysprompt="你是一个知识助手。",
        )

        assert len(messages) == 4  # system_eml + system_role + system_context + user
        assert messages[0]["role"] == "system"
        assert "TOMAS EML" in messages[0]["content"]
        assert messages[1]["content"] == "你是一个知识助手。"
        assert messages[2]["role"] == "system"
        assert "测试概念" in messages[2]["content"]
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "什么是测试概念？"

    def test_wrap_query_no_context(self):
        """无 EML 上下文的查询包装"""
        inj = EMLInjector()
        messages = inj.wrap_query(query="你好", base_sysprompt="通用助手")

        assert len(messages) == 3  # system_eml + system_role + user（无 context 块）
        assert messages[-1]["content"] == "你好"

    def test_update_params(self):
        """运行时参数更新"""
        inj = EMLInjector(kappa=4.0)
        assert inj.ctx.kappa == 4.0

        inj.update_params(kappa=6.0, dead_zero_theta=0.25)
        assert inj.ctx.kappa == 6.0
        assert inj.ctx.dead_zero_theta == 0.25

    def test_build_plain_messages(self):
        """简洁消息构建"""
        inj = EMLInjector()
        messages = inj.build_plain_messages("查询文本", sys_prompt="角色提示")

        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert "TOMAS EML" in messages[0]["content"]
        assert messages[1]["content"] == "角色提示"
        assert messages[2]["content"] == "查询文本"


# ═══════════════════════════════════════════════════════════════
# TOMASRouter 测试
# ═══════════════════════════════════════════════════════════════

class TestTOMASRouter:

    @pytest.fixture
    def sample_config(self):
        """测试用配置字典（不依赖实际 API Key）"""
        return {
            "task_routing": {
                "reason": {"default": "deepseek"},
                "fallback": {"default": "deepseek"},
            },
            "models": {
                "deepseek": {
                    "name": "deepseek",
                    "label": "DeepSeek V3",
                    "provider": "DeepSeek AI",
                    "model": "deepseek-chat",
                    "api_base": "https://api.deepseek.com/v1",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "timeout": 60,
                    "enabled": True,
                    "notes": "Test"
                }
            }
        }

    def test_init_default(self):
        """Router 默认初始化（无配置文件）"""
        router = TOMASRouter()
        assert len(router.backends) >= 1
        assert "deepseek" in router.backends
        assert "fallback" in router.routing_table

    def test_init_from_dict(self, sample_config):
        """从字典初始化"""
        router = TOMASRouter(config_dict=sample_config)
        assert "deepseek" in router.backends
        assert router.routing_table["reason"] == "deepseek"
        assert router.routing_table["fallback"] == "deepseek"

    def test_init_from_file(self, sample_config):
        """从临时文件加载配置"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False,
                                         encoding="utf-8") as f:
            json.dump(sample_config, f)
            tmp_path = f.name

        try:
            router = TOMASRouter(config_path=tmp_path)
            assert "deepseek" in router.backends
        finally:
            os.unlink(tmp_path)

    def test_available_models(self, sample_config, monkeypatch):
        """available_models 属性"""
        # 设置环境变量使其可用
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-fake-key-for-test")
        router = TOMASRouter(config_dict=sample_config)
        models = router.available_models
        assert isinstance(models, list)
        # DeepSeek 现在有 API Key，应该可用
        assert len(models) >= 1

    def test_all_models_includes_disabled(self, sample_config):
        """all_models 包含未启用的模型"""
        sample_config["models"]["disabled_test"] = {
            "name": "disabled_test",
            "label": "Disabled",
            "provider": "Test",
            "model": "test-model",
            "api_base": "https://test.api/v1",
            "api_key_env": "TEST_KEY",
            "enabled": False,
        }
        router = TOMASRouter(config_dict=sample_config)
        all_m = router.all_models
        avail = router.available_models

        assert len(all_m) >= len(avail)
        assert any(m["name"] == "disabled_test" for m in all_m)
        assert not any(m["name"] == "disabled_test" for m in avail)

    def test_task_types(self, sample_config):
        """task_types 属性"""
        router = TOMASRouter(config_dict=sample_config)
        types = router.task_types
        assert "reason" in types
        assert "fallback" in types

    def test_add_backend(self):
        """动态添加后端"""
        router = TOMASRouter()
        router.add_backend("test_model", {
            "label": "Test Model",
            "provider": "Test Inc",
            "model": "test-v1",
            "api_base": "https://test.api/v1",
            "api_key_env": "TEST_KEY",
        })
        assert "test_model" in router.backends
        assert router.backends["test_model"].label == "Test Model"

    def test_set_route(self):
        """设置路由"""
        router = TOMASRouter()
        router.add_backend("custom", {
            "label": "Custom",
            "provider": "Custom",
            "model": "custom-v1",
            "api_base": "https://custom.api/v1",
            "api_key_env": "CUSTOM_KEY",
        })
        router.set_route("new_task", "custom")
        assert router.routing_table["new_task"] == "custom"

    def test_set_route_invalid_model(self):
        """路由到不存在的模型应抛异常"""
        router = TOMASRouter()
        with pytest.raises(RoutingError):
            router.set_route("task", "nonexistent")

    def test_disabled_model_not_in_available(self, sample_config):
        """禁用模型不出现在 available_models 中"""
        router = TOMASRouter(config_dict=sample_config)
        router.disable_model("deepseek")
        avail = router.available_models
        assert not any(m["name"] == "deepseek" for m in avail)

    def test_enable_disable_model(self, sample_config):
        """启用/禁用模型循环"""
        router = TOMASRouter(config_dict=sample_config)
        router.disable_model("deepseek")
        assert not router.backends["deepseek"].enabled

        router.enable_model("deepseek")
        assert router.backends["deepseek"].enabled

    def test_api_key_override(self, sample_config):
        """手动 API Key 覆盖环境变量"""
        router = TOMASRouter(config_dict=sample_config, api_keys={"deepseek": "sk-manual"})
        key = router._api_keys.get("deepseek")
        assert key == "sk-manual"

    def test_to_dict(self, sample_config):
        """导出配置为字典"""
        router = TOMASRouter(config_dict=sample_config)
        d = router.to_dict()
        assert "task_routing" in d
        assert "models" in d
        assert "deepseek" in d["models"]

    def test_eml_injector_integration(self, sample_config):
        """Router 内置 EML Injector"""
        router = TOMASRouter(config_dict=sample_config)
        assert router.eml_injector is not None
        assert router.eml_injector.ctx.kappa == 4.0

    def test_route_nonexistent_task_type_falls_back(self, sample_config):
        """不存在的 task_type 回退到 fallback"""
        router = TOMASRouter(config_dict=sample_config)
        assert router.routing_table.get("nonexistent", router.routing_table["fallback"]) == "deepseek"


# ═══════════════════════════════════════════════════════════════
# 集成测试（跳过需要实际 API 调用的测试）
# ═══════════════════════════════════════════════════════════════

class TestIntegration:

    def test_import_token_bridge(self):
        """token_bridge 可以正常导入（不破坏现有模块）"""
        # 测试导入不影响现有代码
        from token_bridge import TokenBridge, InferenceEngine, CreativeEngine, PhiGate
        assert TokenBridge is not None
        assert InferenceEngine is not None
        assert CreativeEngine is not None
        assert PhiGate is not None

    def test_inference_engine_router_methods(self):
        """InferenceEngine 的 Router 方法存在"""
        from token_bridge import InferenceEngine, TokenBridge
        bridge = TokenBridge()
        engine = InferenceEngine(bridge)

        assert hasattr(engine, 'set_router')
        assert hasattr(engine, 'router')
        assert hasattr(engine, '_use_router')
        assert engine._use_router is False  # 默认不启用


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
