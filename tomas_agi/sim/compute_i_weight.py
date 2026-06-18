# -*- coding: utf-8 -*-
"""
i_weight 后计算脚本（原生 sqlite3 版）
======================================

在 OwnThink 导入完成后运行，为所有 i_weight IS NULL 的行计算 κ-Gate 语义权重。

公式: i_weight = 1.0 + ln(1 + subject_freq) / 10.0
  - subject_freq = 该主体在 knowledge_triples 中的出现次数
  - 范围: [1.0, ~3.0]
  - 含义: 主体越中心，i_weight 越高，κ-Gate 越不容易剪枝它

用法:
    python compute_i_weight.py
    python compute_i_weight.py --dry-run    # 只统计，不更新
    python compute_i_weight.py --batch 5000  # 自定义批次大小

Author: TOMAS Team
"""

from __future__ import annotations

import argparse
import math
import os
import sqlite3
import sys
import time

DB_PATH = os.environ.get("TOMAS_DB_PATH", "D:/tomas-data/tomas.db")
BATCH_SIZE = 10000


def compute_i_weight(db_path: str = DB_PATH, batch_size: int = BATCH_SIZE, dry_run: bool = False):
    """计算所有 i_weight IS NULL 的行的 i_weight 值。"""

    print("=" * 60)
    print("  i_weight 后计算（κ-Gate 语义权重）")
    print("=" * 60)
    print(f"  数据库: {db_path}")
    print(f"  批次大小: {batch_size:,}")
    print(f"  模式: {'DRY RUN（只统计）' if dry_run else 'UPDATE（实际更新）'}")
    print()

    if not os.path.exists(db_path):
        print(f"  ❌ 数据库不存在: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA cache_size=-500000")  # 500MB cache

        # 1. 统计需要更新的行数
        start = time.time()
        null_count = conn.execute(
            "SELECT COUNT(*) FROM knowledge_triples WHERE i_weight IS NULL"
        ).fetchone()[0]
        total_count = conn.execute(
            "SELECT COUNT(*) FROM knowledge_triples"
        ).fetchone()[0]

        print(f"  总行数:        {total_count:>12,}")
        print(f"  待计算行数:    {null_count:>12,}")
        print(f"  已有 i_weight:  {total_count - null_count:>12,}")
        print()

        if null_count == 0:
            print("  ✅ 所有行已有 i_weight，无需计算")
            return

        if dry_run:
            print("  [DRY RUN] 跳过实际更新")
            return

        # 2. 创建临时频率表
        print("  🔄 计算主体频率...")
        freq_start = time.time()
        conn.execute("DROP TABLE IF EXISTS _subject_freq")
        conn.execute("""
            CREATE TEMP TABLE _subject_freq AS
            SELECT subject, COUNT(*) as freq
            FROM knowledge_triples
            WHERE i_weight IS NULL
            GROUP BY subject
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS _idx_sf_subject ON _subject_freq(subject)")

        freq_count = conn.execute("SELECT COUNT(*) FROM _subject_freq").fetchone()[0]
        freq_time = time.time() - freq_start
        print(f"  独立主体数: {freq_count:,}（耗时 {freq_time:.1f}s）")

        # 3. 分批更新 i_weight
        print()
        print("  🔄 更新 i_weight...")
        update_start = time.time()

        result = conn.execute("""
            SELECT kt.id, sf.freq
            FROM knowledge_triples kt
            INNER JOIN _subject_freq sf ON kt.subject = sf.subject
            WHERE kt.i_weight IS NULL
            ORDER BY kt.id
        """)

        updated = 0
        batch = []
        last_report = time.time()

        for row_id, freq in result:
            i_weight = 1.0 + math.log(1.0 + freq) / 10.0
            batch.append((i_weight, row_id))

            if len(batch) >= batch_size:
                conn.executemany(
                    "UPDATE knowledge_triples SET i_weight = ? WHERE id = ?",
                    batch
                )
                conn.commit()
                updated += len(batch)
                batch = []

                now = time.time()
                if now - last_report >= 5.0:
                    elapsed = now - update_start
                    rate = updated / elapsed if elapsed > 0 else 0
                    pct = updated / null_count * 100
                    remaining = (null_count - updated) / rate if rate > 0 else 0
                    print(
                        f"  📍 {updated:>10,} / {null_count:,} ({pct:.1f}%) "
                        f"| {rate:,.0f}/s | ETA {remaining/60:.1f}min"
                    )
                    last_report = now

        if batch:
            conn.executemany(
                "UPDATE knowledge_triples SET i_weight = ? WHERE id = ?",
                batch
            )
            conn.commit()
            updated += len(batch)

        update_time = time.time() - update_start
        print(f"  ✅ 更新完成: {updated:,} 行（{update_time:.1f}s, {updated/update_time:,.0f}/s）")

        # 4. 清理临时表
        conn.execute("DROP TABLE IF EXISTS _subject_freq")
        conn.commit()

        # 5. 验证分布
        print()
        print("  📈 i_weight 分布:")
        for threshold in [0, 1.0, 1.1, 1.2, 1.5, 2.0, 2.5, 3.0]:
            cnt = conn.execute(
                "SELECT COUNT(*) FROM knowledge_triples WHERE i_weight >= ?", (threshold,)
            ).fetchone()[0]
            pct = cnt / total_count * 100
            print(f"    i_weight >= {threshold:4.1f}: {cnt:>12,} ({pct:.1f}%)")

        # 6. 统计 NULL（应该为 0）
        remaining_null = conn.execute(
            "SELECT COUNT(*) FROM knowledge_triples WHERE i_weight IS NULL"
        ).fetchone()[0]
        print(f"\n  剩余 NULL: {remaining_null:,}")

        elapsed = time.time() - start
        print(f"\n  ✅ 总耗时: {elapsed/60:.1f} 分钟")
        print("=" * 60)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="i_weight 后计算（κ-Gate 语义权重）")
    parser.add_argument("--db", type=str, default=DB_PATH, help="数据库路径")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE, help="批次大小")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不更新")
    args = parser.parse_args()

    compute_i_weight(db_path=args.db, batch_size=args.batch, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
