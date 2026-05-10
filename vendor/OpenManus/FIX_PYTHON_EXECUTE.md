# python_execute 长字符串 JSON 参数问题修复

## 问题描述

当传递长的 Python 代码字符串给 `python_execute` 工具时，JSON 参数解析会失败。错误信息：
```
arguments:{"code": "# 创建完整的建筑设备管理网页\nhtml_content = '''<!DOCTYPE html>\n<html lang=\"zh-CN\">...
，基本上好像是因为内容太长有报错，内容短都没问题
```

**根本原因分析：**

### 问题1：参数编码机制
在 `app/utils/arg_serialization.py` 中，`encode_args()` 函数会自动对长字符串进行 Base64 编码：

```python
if isinstance(v, str) and ("\n" in v or '"' in v or len(v) > 200):
    out[f"{k}_b64"] = base64.b64encode(v.encode("utf-8")).decode("ascii")
```

当代码包含换行符、双引号或超过 200 字符时，会被编码为 `code_b64` 字段（而不是 `code`）。

### 问题2：python_execute 参数处理不完整
原始的 `python_execute` 实现只有基础的参数处理逻辑，没有处理 Base64 编码的 `code_b64` 字段。

## 修复方案

### 修改文件：[app/tool/python_execute.py](app/tool/python_execute.py)

添加了多策略参数处理机制：

```python
# 策略1：尝试从 raw_args 中解码 JSON
try:
    raw_args = kwargs.get("raw_args", "{}")
    if isinstance(raw_args, str):
        decoded = decode_args(raw_args)  # 自动处理 _b64 后缀
        code = decoded.get("code", "")
except Exception:
    pass

# 策略2：尝试直接处理 code_b64（Base64 编码的代码）
if not code:
    try:
        code_b64 = kwargs.get("code_b64")
        if code_b64:
            code = base64.b64decode(code_b64).decode("utf-8")
    except Exception:
        pass

# 策略3：回退到直接的 code 参数
if not code:
    code = kwargs.get("code", "")
```

## 工作流程

### 当代码过长时（>200 字符或包含特殊字符）

```
原始参数: {"code": "...长代码..."}
         ↓
encode_args() 编码
         ↓
{"code_b64": "aGVsbG8gd29ybGQ=..."}
         ↓
execute() 方法
  - 策略1：decode_args() 自动恢复 code 字段 ✓
  - 策略2：或直接解码 code_b64
  - 策略3：回退到 code
```

### 当代码较短时（<200 字符且无特殊字符）

```
原始参数: {"code": "...短代码..."}
         ↓
encode_args() 保持不变
         ↓
{"code": "..."}
         ↓
execute() 方法
  - 策略3：直接从 kwargs 获取 code ✓
```

## 验证

运行测试脚本验证修复：

```bash
# 快速验证编码/解码
python test_quick_fix.py

# 完整测试所有场景
python test_python_execute_fix.py
```

### 测试结果

✓ 编码/解码逻辑正确
✓ 长字符串（>2500 字符）能被正确编码和解码
✓ Base64 编解码成功

## 修改的文件

- [app/tool/python_execute.py](app/tool/python_execute.py) - 添加了多策略参数处理
- `app/utils/arg_serialization.py` - 无需修改（逻辑已经正确）

## 向后兼容性

✓ 完全向后兼容
- 短字符串继续直接传递
- 长字符串现在也能正确处理
- 所有三种参数传递方式都支持
