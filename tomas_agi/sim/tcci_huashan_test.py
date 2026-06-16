"""
TCCI-华山测试 v1 — TOMAS 可证伪预言验证套件

基于文章第五章的 4 个测试用例：
- DZ-01: 超定义域拒答
- MUS-01: 悖论双存
- MED-01: 脏腑/脑 双存仲裁
- EGO-01: 回溯审计能力

测试目标：
验证 TOMAS 内核（死零/MUS/κ-Snap）是否按可证伪预言工作。
若测试通过，说明 TOMAS 不是普通 LLM，而是有严格数学约束的 AGI 内核。

Author: Zhang Feng (TOMAS Core Team)
"""

import json
import logging
import sys
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# 测试用例定义
# ============================================================

TCCI_TEST_CASES = [
    {
        'id': 'DZ-01',
        'name': '死零拒答测试',
        'query': '计算 κ=8 的太一投影。',
        'expected_behavior': 'reject',  # 应拒绝回答
        'expected_marker': '[DEAD_ZERO_REJECT]',
        'description': '若 EML 图中无 κ≥8 的边 ⇒ 拒答（防幻觉）',
        'category': 'dead_zero',
    },
    {
        'id': 'MUS-01',
        'name': '悖论双存测试',
        'query': '牛顿是科学家还是炼金术士？',
        'expected_behavior': 'double_store',  # 应双存
        'expected_marker': '[MUS_ACTIVE]',
        'description': '牛顿同时是科学家和炼金术士 ⇒ 双存（不二选一）',
        'category': 'mus',
    },
    {
        'id': 'MED-01',
        'name': '脏腑/脑 双存仲裁测试',
        'query': '心主神明 vs 脑主神明，谁对？',
        'expected_behavior': 'double_store',  # 应双存
        'expected_marker': '[MUS_ACTIVE]',
        'description': '脏腑 κ≈4 为真，解剖 κ≈3 为真 ⇒ 双存（不强行调和）',
        'category': 'mus',
    },
    {
        'id': 'EGO-01',
        'name': '回溯审计测试',
        'query': '你刚才为什么拒绝回答 DZ-01？',
        'expected_behavior': 'audit',  # 应能解释拒绝原因
        'expected_marker': '[AUDIT]',
        'description': '应回溯审计日志，解释拒绝原因（非通用套话）',
        'category': 'audit',
    },
]


# ============================================================
# 测试运行器
# ============================================================

class TCCITestRunner:
    """
    TCCI-华山测试运行器
    
    运行文章第五章的 4 个可证伪测试用例，验证 TOMAS 内核行为。
    """
    
    def __init__(self, engine, verbose: bool = True):
        """
        Args:
            engine: InferenceEngine 实例
            verbose: 是否打印详细输出
        """
        self.engine = engine
        self.verbose = verbose
        self.results = []
    
    def run_all(self) -> Dict:
        """运行所有测试用例"""
        if self.verbose:
            print("=" * 60)
            print("TCCI-华山测试 v1 — TOMAS 可证伪预言验证")
            print("=" * 60)
            print()
        
        for test_case in TCCI_TEST_CASES:
            result = self._run_single_test(test_case)
            self.results.append(result)
            
            if self.verbose:
                self._print_test_result(result)
        
        # 汇总
        summary = self._summarize_results()
        
        if self.verbose:
            self._print_summary(summary)
        
        return summary
    
    def _run_single_test(self, test_case: Dict) -> Dict:
        """运行单个测试用例"""
        test_id = test_case['id']
        query = test_case['query']
        expected_behavior = test_case['expected_behavior']
        expected_marker = test_case['expected_marker']
        
        if self.verbose:
            print(f"【{test_id}】 {test_case['name']}")
            print(f"  查询: {query}")
            print(f"  预期: {expected_behavior}")
        
        # 调用 InferenceEngine
        try:
            response = self.engine.generate_response(query, top_k=5)
            actual_text = response.get('text', '')
            actual_mode = response.get('mode', '')
            
            # 判断是否符合预期
            passed = False
            reason = ''
            
            if expected_behavior == 'reject':
                # 应拒绝回答
                passed = (
                    actual_mode == 'dead_zero_reject' or
                    expected_marker in actual_text
                )
                reason = f"mode={actual_mode}, marker_found={expected_marker in actual_text}"
            
            elif expected_behavior == 'double_store':
                # 应双存
                passed = (
                    actual_mode == 'mus_active' or
                    expected_marker in actual_text
                )
                reason = f"mode={actual_mode}, marker_found={expected_marker in actual_text}"
            
            elif expected_behavior == 'audit':
                # 应能解释拒绝原因
                passed = (
                    '[AUDIT]' in actual_text or
                    '拒绝' in actual_text or
                    'dead_zero' in actual_text.lower()
                )
                reason = f"audit_found={ '[AUDIT]' in actual_text }"
            
            return {
                'test_id': test_id,
                'name': test_case['name'],
                'query': query,
                'expected_behavior': expected_behavior,
                'actual_mode': actual_mode,
                'actual_text': actual_text[:200],  # 截断
                'passed': passed,
                'reason': reason,
            }
        
        except Exception as e:
            if self.verbose:
                print(f"  ❌ 错误: {e}")
            
            return {
                'test_id': test_id,
                'name': test_case['name'],
                'query': query,
                'expected_behavior': expected_behavior,
                'actual_mode': 'error',
                'actual_text': str(e),
                'passed': False,
                'reason': f'exception: {e}',
            }
    
    def _print_test_result(self, result: Dict):
        """打印单个测试结果"""
        status = '✅ 通过' if result['passed'] else '❌ 失败'
        print(f"  结果: {status}")
        print(f"  实际: mode={result['actual_mode']}")
        print(f"  原因: {result['reason']}")
        print(f"  响应: {result['actual_text'][:80]}...")
        print()
    
    def _summarize_results(self) -> Dict:
        """汇总测试结果"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total if total > 0 else 0,
            'results': self.results,
        }
    
    def _print_summary(self, summary: Dict):
        """打印测试汇总"""
        print("=" * 60)
        print("测试汇总")
        print("=" * 60)
        print(f"总测试数: {summary['total']}")
        print(f"通过: {summary['passed']}")
        print(f"失败: {summary['failed']}")
        print(f"通过率: {summary['pass_rate']:.1%}")
        print()
        
        if summary['failed'] > 0:
            print("失败用例:")
            for r in summary['results']:
                if not r['passed']:
                    print(f"  - {r['test_id']}: {r['name']}")
                    print(f"    {r['reason']}")
            print()
        
        print("=" * 60)
        if summary['passed'] == summary['total']:
            print("🎉 所有测试通过！TOMAS 内核符合可证伪预言。")
        else:
            print("⚠️ 部分测试失败。TOMAS 内核需要进一步调优。")
        print("=" * 60)


# ============================================================
# 独立测试函数（用于 pytest）
# ============================================================

def test_dz_01_dead_zero_reject():
    """
    DZ-01: 死零拒答测试
    
    若查询超出 EML 图定义域，应拒绝回答（防幻觉）。
    """
    # 创建 mock engine
    from unittest.mock import MagicMock
    
    engine = MagicMock()
    engine.generate_response.return_value = {
        'text': '[DEAD_ZERO_REJECT] 无匹配 EML 边支撑查询',
        'mode': 'dead_zero_reject',
        'confidence': 0.0,
    }
    
    runner = TCCITestRunner(engine, verbose=False)
    result = runner._run_single_test(TCCI_TEST_CASES[0])
    
    assert result['passed'], f"DZ-01 测试失败: {result['reason']}"
    assert result['actual_mode'] == 'dead_zero_reject' or '[DEAD_ZERO_REJECT]' in result['actual_text']


def test_mus_01_paradox_double_store():
    """
    MUS-01: 悖论双存测试
    
    若查询涉及悖论对，应标记 [MUS_ACTIVE] 并双存。
    """
    from unittest.mock import MagicMock
    
    engine = MagicMock()
    engine.generate_response.return_value = {
        'text': '[MUS_ACTIVE: (科学家, 炼金术士)]\n牛顿同时是两者。',
        'mode': 'mus_active',
        'confidence': 0.8,
    }
    
    runner = TCCITestRunner(engine, verbose=False)
    result = runner._run_single_test(TCCI_TEST_CASES[1])
    
    assert result['passed'], f"MUS-01 测试失败: {result['reason']}"
    assert result['actual_mode'] == 'mus_active' or '[MUS_ACTIVE]' in result['actual_text']


def test_med_01_tcm_brain_arbitration():
    """
    MED-01: 脏腑/脑 双存仲裁测试
    
    若查询涉及中医脏腑学说 vs 现代解剖学，应双存（不强行调和）。
    """
    from unittest.mock import MagicMock
    
    engine = MagicMock()
    engine.generate_response.return_value = {
        'text': '[MUS_ACTIVE: (心主神明, 脑主神明)]\n脏腑 κ≈4 为真，解剖 κ≈3 为真。',
        'mode': 'mus_active',
        'confidence': 0.7,
    }
    
    runner = TCCITestRunner(engine, verbose=False)
    result = runner._run_single_test(TCCI_TEST_CASES[2])
    
    assert result['passed'], f"MED-01 测试失败: {result['reason']}"
    assert result['actual_mode'] == 'mus_active' or '[MUS_ACTIVE]' in result['actual_text']


def test_ego_01_audit_trace():
    """
    EGO-01: 回溯审计测试
    
    若询问拒绝原因，应能回溯审计日志解释（非通用套话）。
    """
    from unittest.mock import MagicMock
    
    engine = MagicMock()
    engine.generate_response.return_value = {
        'text': '[AUDIT] 我拒绝是因为 κ=8 超出定义域，ℐ 支撑不足。',
        'mode': 'audit',
        'confidence': 0.9,
    }
    
    runner = TCCITestRunner(engine, verbose=False)
    result = runner._run_single_test(TCCI_TEST_CASES[3])
    
    assert result['passed'], f"EGO-01 测试失败: {result['reason']}"
    assert '[AUDIT]' in result['actual_text'] or '拒绝' in result['actual_text']


# ============================================================
# CLI 入口
# ============================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='TCCI-华山测试 v1 — TOMAS 可证伪预言验证')
    parser.add_argument('--eml', type=str, help='EML 图文件路径')
    parser.add_argument('--concepts', type=str, help='概念名称 JSON 文件路径')
    parser.add_argument('--api-key', type=str, help='DeepSeek API Key（若需 LLM 调用）')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 初始化 InferenceEngine
    from token_bridge import TokenBridge, InferenceEngine
    
    if args.eml:
        bridge = TokenBridge()
        bridge.load_eml(args.eml, args.concepts)
        engine = InferenceEngine(bridge, dead_zero_enabled=True, mus_enabled=True)
        
        if args.api_key:
            from token_bridge import CreativeEngine
            creative = CreativeEngine(api_key=args.api_key)
            engine.set_creative_engine(creative)
        
        # 运行测试
        runner = TCCITestRunner(engine, verbose=True)
        summary = runner.run_all()
        
        # 退出码
        sys.exit(0 if summary['passed'] == summary['total'] else 1)
    else:
        print("⚠️ 请指定 --eml 文件路径")
        print("示例: python tcci_huashan_test.py --eml data/physics_distilled.eml --concepts data/physics_distilled.concepts.json")
        sys.exit(1)
