"""
修复数据库中的 BIM URL
将 embed URL 替换为正确的项目 URL
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from backend.database import get_db_context, Task
import json


def fix_bim_urls():
    """修复所有任务的 BIM URL"""
    with get_db_context() as db:
        tasks = db.query(Task).filter(Task.result_json.isnot(None)).all()

        fixed_count = 0
        for task in tasks:
            result = task.result_json

            # 检查是否有 bim_url 和 raw.bim_results
            if not result or 'raw' not in result:
                continue

            bim_results = result.get('raw', {}).get('bim_results', {})
            if not bim_results or bim_results.get('status') != 'success':
                continue

            # 获取正确的 URL
            correct_url = bim_results.get('url')
            current_url = result.get('bim_url')

            if correct_url and current_url != correct_url:
                print(f"Task {task.id}:")
                print(f"  Current: {current_url}")
                print(f"  Correct: {correct_url}")

                # 更新 bim_url
                result['bim_url'] = correct_url
                task.result_json = result
                fixed_count += 1

        if fixed_count > 0:
            db.commit()
            print(f"\n已修复 {fixed_count} 个任务的 BIM URL")
        else:
            print("没有需要修复的任务")


if __name__ == '__main__':
    print("开始修复 BIM URL...")
    fix_bim_urls()
    print("完成！")
