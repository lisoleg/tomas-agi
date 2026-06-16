"""
TOMAS-MemOS 融合层集成包装器
Author: Zhang Feng / TOMAS Team
Date: 2026-06-16

为 token_bridge.py 提供 MemOS 融合层集成接口。
使用方法：
    from .memos_integration import enable_memos_for_engine
    
    # 在 main() 中
    if args.enable_memos:
        enable_memos_for_engine(engine, args)
"""

import sys
import os
from typing import Optional, Dict, Any

from .memos_fusion import TOMAS_Mem_OS_Fusion, MemoryRecord
from .psi_anchor import PsiAnchor, PsiAnchorManager


def enable_memos_for_engine(engine, args) -> TOMAS_Mem_OS_Fusion:
    """
    为 InferenceEngine 启用 MemOS 融合层
    
    Args:
        engine: InferenceEngine 实例
        args: argparse 参数
        
    Returns:
        TOMAS_Mem_OS_Fusion 实例
    """
    # 初始化融合层
    # 自动从 args 中读取 EML 路径（复用 token_bridge 的 --load / --concepts）
    eml_path = getattr(args, 'load', None)  # --load 参数
    concepts_path = getattr(args, 'concepts', None)  # --concepts 参数
    
    fusion = TOMAS_Mem_OS_Fusion(
        store_path=args.memos_store,
        theta_dead=args.theta_dead,
        theta_write=args.memos_theta_write,
        theta_archieve=0.1,
        enable_mus=not args.disable_mus,
        enable_psi=args.memos_psi,
        enable_kappa_gate=args.memos_kappa_gate,
        eml_path=eml_path,
        concepts_json_path=concepts_path,
    )
    
    # 将 fusion 附加到 engine
    engine._memos_fusion = fusion
    
    #  monkey-patch generate_response 来集成融合层
    original_generate = engine.generate_response
    
    def patched_generate_response(text: str, top_k: int = 5,
                                  force_translator: bool = False,
                                  force_creative: bool = False,
                                  kappa: float = 0.0) -> Dict[str, Any]:
        """
        打了补丁的 generate_response：集成 MemOS 融合层
        """
        # Step 1: 写入记忆（死零校验 + MUS 双存 + ψ-锚）
        context = {
            "concepts": [],  # 未来可从 EML 查询结果提取
            "self_state": "持有'回答用户问题'的元意向",
            "current_kappa": int(kappa) if kappa > 0 else 4,
            "emotion_tone": None,
        }
        
        write_result = fusion.write_memory(text, context)
        
        if write_result["status"] == "rejected":
            # 死零拒绝：不写入记忆，但继续推理
            print(f"[MemOS] {write_result['message']}")
        
        # Step 2: 回忆记忆（κ-Gate 激活 + κ-Snap 裁决）
        current_kappa = int(kappa) if kappa > 0 else 4
        recall_result = fusion.recall_memory(text, current_kappa, context)
        
        # Step 3: 调用原始推理
        response = original_generate(
            text, top_k, force_translator, force_creative, kappa
        )
        
        # Step 4: 将记忆信息注入响应
        if recall_result["status"] == "success":
            # 在响应前添加记忆回溯信息
            memory_info = f"[MemOS 记忆回溯] 激活 {recall_result['activated_count']} 条记忆"
            if recall_result.get("mus_count", 0) > 0:
                memory_info += f"，其中 {recall_result['mus_count']} 条 MUS 双存"
            
            # 将记忆信息添加到响应的 matched_concepts 中
            if "matched_concepts" not in response:
                response["matched_concepts"] = []
            
            # 添加记忆记录到响应
            response["memos_recall"] = recall_result
            response["text"] = f"{memory_info}\n\n{response['text']}"
        
        # Step 5: 添加 ψ-锚信息（如果有）
        if write_result.get("psi_anchor"):
            psi_info = PsiAnchorManager.format_for_response(
                PsiAnchor.from_dict(write_result["psi_anchor"])
            )
            response["memos_psi_anchor"] = psi_info
        
        return response
    
    # 替换 generate_response 方法
    engine.generate_response = patched_generate_response
    
    print(f"\n🧠 TOMAS-MemOS 融合层已启用")
    print(f"  死零阈值 θ_dead = {args.theta_dead}")
    print(f"  ψ-锚: {'✅ 启用' if args.memos_psi else '❌ 禁用'}")
    print(f"  κ-Gate: {'✅ 启用' if args.memos_kappa_gate else '❌ 禁用'}")
    print(f"  MUS 双存: {'✅ 启用' if not args.disable_mus else '❌ 禁用'}")
    
    return fusion


def get_memos_stats(engine) -> Optional[Dict[str, Any]]:
    """获取 MemOS 融合层统计信息"""
    if hasattr(engine, "_memos_fusion"):
        return engine._memos_fusion.get_stats()
    return None


# 导出
__all__ = ["enable_memos_for_engine", "get_memos_stats", "TOMAS_Mem_OS_Fusion"]
