"""
File Download Routes
"""
import io
import os
import zipfile
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from backend.database import get_db, Task, TaskFile
from backend.api.middleware import get_current_user
from backend.api.services import decode_token
from backend.database.models import User

router = APIRouter(prefix="/file", tags=["文件"])


@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载任务输出文件"""
    task_file = db.query(TaskFile).join(Task).filter(
        TaskFile.id == file_id,
        Task.user_id == current_user.id
    ).first()

    if not task_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = task_file.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件已被删除")

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream"
    )


@router.get("/view")
async def view_file(
    path: str = Query(..., description="文件相对路径")
):
    """在线查看文件（用于预览图片等）- 无需认证"""
    # 安全检查：防止路径遍历攻击
    if ".." in path or path.startswith("/") or path.startswith("\\"):
        raise HTTPException(status_code=400, detail="非法路径")

    # 构建完整路径（相对于项目根目录）
    base_dir = os.path.abspath(".")
    full_path = os.path.join(base_dir, path)

    # 确保文件在项目目录内
    if not full_path.startswith(base_dir):
        raise HTTPException(status_code=400, detail="非法路径")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 根据文件扩展名设置 media_type
    ext = os.path.splitext(full_path)[1].lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }
    media_type = media_type_map.get(ext, "application/octet-stream")

    return FileResponse(
        path=full_path,
        media_type=media_type
    )


@router.get("/package/{task_id}")
async def package_task_files(
    task_id: str,
    token: str = Query(..., description="JWT token"),
    db: Session = Depends(get_db)
):
    """打包下载任务所有输出文件（ZIP）"""
    # 从 query param 解析 token（window.open 无法设置 Header）
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的 token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="无效的 token")

    from backend.database.models import User as UserModel
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "success" or not task.result_json:
        raise HTTPException(status_code=400, detail="任务尚未完成或无输出文件")

    result = task.result_json
    base_dir = os.path.abspath(".")

    # 收集所有文件路径
    file_paths: list[tuple[str, str]] = []  # (绝对路径, ZIP内路径)

    def _add(path: str, arcname: str | None = None):
        if not path:
            return
        # 兼容相对路径和绝对路径
        full = path if os.path.isabs(path) else os.path.join(base_dir, path)
        full = os.path.normpath(full)
        if os.path.exists(full) and os.path.isfile(full):
            name = arcname or os.path.basename(full)
            file_paths.append((full, name))

    # 报告
    _add(result.get("report_file", ""), "report/" + os.path.basename(result.get("report_file", "") or "report.pdf"))

    # CAD图纸
    for key, path in (result.get("files") or {}).items():
        if isinstance(path, str):
            _add(path, f"cad/{os.path.basename(path)}")

    # 有限元可视化
    for key, path in (result.get("visualizations", {}).get("static") or {}).items():
        if isinstance(path, str):
            _add(path, f"visualizations/{os.path.basename(path)}")
    for key, path in (result.get("visualizations", {}).get("interactive") or {}).items():
        if isinstance(path, str):
            _add(path, f"visualizations/{os.path.basename(path)}")

    # IFC模型
    _add(result.get("ifc_path", ""), "bim/" + os.path.basename(result.get("ifc_path", "") or "model.ifc"))

    if not file_paths:
        raise HTTPException(status_code=404, detail="没有可下载的文件")

    # 在内存中打包
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for full_path, arcname in file_paths:
            zf.write(full_path, arcname)
    buf.seek(0)

    zip_filename = f"structural_design_{task_id[:8]}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )


@router.get("/download")
async def download_file_by_path(
    path: str = Query(..., description="文件相对路径")
):
    """通过路径下载文件 - 无需认证"""
    # 安全检查：防止路径遍历攻击
    if ".." in path or path.startswith("/") or path.startswith("\\"):
        raise HTTPException(status_code=400, detail="非法路径")

    # 构建完整路径（相对于项目根目录）
    base_dir = os.path.abspath(".")
    full_path = os.path.join(base_dir, path)

    # 确保文件在项目目录内
    if not full_path.startswith(base_dir):
        raise HTTPException(status_code=400, detail="非法路径")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=full_path,
        filename=os.path.basename(full_path),
        media_type="application/octet-stream"
    )
