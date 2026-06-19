"""
OwnThink CSV → SQLite 断点续传导入器（原生 sqlite3 版）
=========================================================
绕过 SQLAlchemy，直接用 sqlite3，避免 "database is locked" 问题。

用法：
  python resume_import.py --skip 80000000
"""

import os
import sys
import csv
import re
import time
import sqlite3
import argparse
from datetime import datetime

DB_PATH = "D:/tomas-data/tomas.db"
CSV_PATH = "D:/ownthink_v2/ownthink_v2.csv"
BATCH_SIZE = 5000  # 每批插入行数（原 50000，避免 MemoryError）
PROGRESS_INTERVAL = 200000

# 伪概念过滤器
_DATE_PATTERNS = [
    re.compile(r'^\d{4}年\d{1,2}月\d{1,2}日?$'),
    re.compile(r'^\d{4}年\d{1,2}月$'),
    re.compile(r'^\d{4}年$'),
    re.compile(r'^公元前\d+年'),
    re.compile(r'^公元\d+年'),
    re.compile(r'^\d{1,2}世纪(\d{1,2})?年代?$'),
    re.compile(r'^[春夏秋冬]季$'),
    re.compile(r'^\d{1,2}[月日号]$'),
    re.compile(r'^(?:周|星期)[一二三四五六日天]$'),
    re.compile(r'^\d{4}-\d{2}-\d{2}$'),
    re.compile(r'^\d{2}:\d{2}(:\d{2})?$'),
]
_NUMBER_PATTERNS = [
    re.compile(r'^[\d\s.,，。、%％‰+\-×÷=<>≥≤π∞]+$'),
    re.compile(r'^[\d.]+(?:万|亿|k|K|M|G|T)?(?:个|条|人|次|项)?$'),
    re.compile(r'^v?\d+(\.\d+)*([a-zA-Z]*)$'),
    re.compile(r'^第?[一二三四五六七八九十百千\d]+[章节卷册页版]$'),
]
_MEASURE_PATTERN = re.compile(
    r'^[\d.]+(?:km|m|cm|mm|kg|g|mg|℃|℉|%|公里|米|厘米|毫米|千克|克|毫升|升|公顷|亩|秒分小时天周年)$',
    re.IGNORECASE,
)

def is_pseudo_concept(s):
    s = s.strip()
    if len(s) == 0 or len(s) < 2:
        return True
    for p in _DATE_PATTERNS:
        if p.match(s):
            return True
    for p in _NUMBER_PATTERNS:
        if p.match(s):
            return True
    if _MEASURE_PATTERN.match(s):
        return True
    if s.startswith(('http://', 'https://', 'www.', 'ftp://')):
        return True
    if '@' in s and '.' in s.split('@')[-1]:
        return True
    if re.match(r'^[\d\-+\s()（）]{7,15}$', s):
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="OwnThink 断点续传导入（原生 sqlite3）")
    parser.add_argument("--skip", "-s", type=int, default=0, help="跳过 CSV 前 N 行")
    parser.add_argument("--input", "-i", type=str, default=CSV_PATH)
    parser.add_argument("--db", "-d", type=str, default=DB_PATH)
    parser.add_argument("--batch", "-b", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ CSV 不存在: {args.input}")
        sys.exit(1)

    # 连接 DB（原生 sqlite3，WAL 模式 + 30s busy_timeout）
    conn = sqlite3.connect(args.db, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA cache_size=-500000")  # 500MB cache

    cursor = conn.cursor()

    # 检查当前行数
    cursor.execute("SELECT COUNT(*) FROM knowledge_triples")
    current_count = cursor.fetchone()[0]
    print(f"当前 knowledge_triples: {current_count:,} 行")

    print("=" * 60)
    print("  OwnThink 断点续传导入（原生 sqlite3）")
    print("=" * 60)
    print(f"  CSV:    {args.input}")
    print(f"  DB:     {args.db}")
    print(f"  批次:   {args.batch:,}")
    print(f"  跳过:   {args.skip:,} 行")
    print()

    total_rows = 0
    inserted = 0
    duplicates = 0
    pseudo_filtered = 0
    batch = []
    start_time = time.time()
    last_progress = start_time

    def flush():
        nonlocal inserted, duplicates, batch
        if not batch:
            return
        try:
            cursor.executemany(
                "INSERT OR IGNORE INTO knowledge_triples (subject, predicate, object, created_at) VALUES (?, ?, ?, ?)",
                batch
            )
            inserted += cursor.rowcount
            duplicates += (len(batch) - cursor.rowcount)
            conn.commit()
        except sqlite3.OperationalError as e:
            print(f"  ⚠️ DB 错误: {e}, 等待 5s 重试...")
            time.sleep(5)
            try:
                cursor.executemany(
                    "INSERT OR IGNORE INTO knowledge_triples (subject, predicate, object, created_at) VALUES (?, ?, ?, ?)",
                    batch
                )
                inserted += cursor.rowcount
                duplicates += (len(batch) - cursor.rowcount)
                conn.commit()
            except Exception as e2:
                print(f"  ❌ 重试失败: {e2}")
        batch.clear()

    try:
        with open(args.input, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.reader(f)
            # 跳过表头
            header = next(reader, None)
            if header:
                print(f"  ⏭ 跳过表头: {header[:3]}")

            # 断点续传：跳过已导入的行
            if args.skip > 0:
                print(f"  ⏭ 跳过前 {args.skip:,} 行...")
                skip_start = time.time()
                for i in range(args.skip):
                    try:
                        next(reader, None)
                    except (csv.Error, StopIteration):
                        break
                print(f"  ⏭ 跳过完成 ({time.time() - skip_start:.1f}s)")

            for row in reader:
                if len(row) < 3:
                    continue
                total_rows += 1

                try:
                    entity = row[0].strip()
                    predicate = row[1].strip()
                    value = row[2].strip()
                except (UnicodeDecodeError, csv.Error):
                    continue

                if not entity or not predicate:
                    continue
                if is_pseudo_concept(entity):
                    pseudo_filtered += 1
                    continue
                if is_pseudo_concept(value) or len(value) <= 1:
                    pseudo_filtered += 1
                    continue

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                batch.append((entity, predicate, value, now))

                if len(batch) >= args.batch:
                    flush()

                if total_rows % PROGRESS_INTERVAL == 0:
                    now_t = time.time()
                    elapsed = now_t - start_time
                    rate = total_rows / elapsed if elapsed > 0 else 0
                    interval = now_t - last_progress
                    last_progress = now_t
                    print(
                        f"  📍 {total_rows:>12,} | "
                        f"已插 {inserted:>10,} | "
                        f"重复 {duplicates:>8,} | "
                        f"过滤 {pseudo_filtered:>8,} | "
                        f"{elapsed/3600:.1f}h | "
                        f"{rate:,.0f}/s"
                    )

            flush()

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断，保存中...")
        flush()
    finally:
        conn.close()

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print("  ✅ 导入完成")
    print("=" * 60)
    print(f"  新处理行数:    {total_rows:>12,}")
    print(f"  新插入:        {inserted:>12,}")
    print(f"  重复跳过:      {duplicates:>12,}")
    print(f"  伪概念过滤:    {pseudo_filtered:>12,}")
    print(f"  耗时:          {elapsed/3600:.2f}h ({elapsed:.0f}s)")
    print(f"  速率:          {total_rows/elapsed:,.0f}/s" if elapsed > 0 else "")


if __name__ == "__main__":
    main()
