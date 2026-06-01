"""
SpeckleExporter - 将结构设计结果推送到Speckle BIM平台
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class SpeckleExporter:
    """将DesignProposal + AnalysisResults + EvaluationReport推送到Speckle。"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: config.toml中[speckle]节的内容
        """
        self.server_url = config.get('server_url', 'https://app.speckle.systems')
        self.token = config.get('token', '')
        self.project_id = config.get('project_id', '')
        self._client = None

    def _get_client(self):
        if self._client is None:
            from specklepy.api.client import SpeckleClient
            self._client = SpeckleClient(host=self.server_url)
            self._client.authenticate_with_token(self.token)
        return self._client

    def export(
        self,
        design_proposal: Dict,
        analysis_results: Dict,
        evaluation_report: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        推送结构设计结果到Speckle。
        使用 specklepy 2.x API（stream/branch/commit 模型）。

        Returns:
            {'status': 'success', 'url': '...', 'model_id': '...'}
            {'status': 'error', 'error': '...'}
        """
        try:
            from specklepy.objects.base import Base
            from specklepy.transports.server import ServerTransport
            from specklepy.api import operations

            client = self._get_client()
            structure_type = design_proposal.get('type', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            branch_name = f"{structure_type}/{timestamp}"

            # specklepy 2.x: stream_id = project_id，创建 branch 对应 3.x 的 model
            stream_id = self.project_id
            branch_id = client.branch.create(
                stream_id=stream_id,
                name=branch_name,
                description=f"{structure_type} 结构设计方案"
            )

            # 构建 Base 对象
            base = self._build_base_object(design_proposal, analysis_results, evaluation_report)

            # 推送对象
            transport = ServerTransport(client=client, stream_id=stream_id)
            obj_id = operations.send(base, [transport])

            # 创建 commit（对应 3.x 的 version）
            commit_id = client.commit.create(
                stream_id=stream_id,
                object_id=obj_id,
                branch_name=branch_name,
                message=f"{structure_type} 结构设计方案 {timestamp}",
            )

            # 新 UI URL 格式：/projects/{id}/models/{branch_id}@{commit_id}
            url = f"{self.server_url}/projects/{stream_id}/models/{branch_id}@{commit_id}"
            embed_url = f"{self.server_url}/embed?stream={stream_id}&commit={commit_id}"
            return {'status': 'success', 'url': url, 'embed_url': embed_url, 'model_id': branch_id}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def _build_base_object(
        self,
        design_proposal: Dict,
        analysis_results: Dict,
        evaluation_report: Optional[Dict],
    ):
        from specklepy.objects.base import Base

        structure_type = design_proposal.get('type', 'unknown')
        geometry = design_proposal.get('geometry', {})
        material = design_proposal.get('material', {})
        results = analysis_results.get('results', {})

        base = Base()
        base.speckle_type = 'Objects.Structural.StructuralModel'
        base['structure_type'] = structure_type
        base['name'] = f"{structure_type} 结构设计"

        # 截面与材料
        base['section'] = {
            'width_m': geometry.get('width'),
            'height_m': geometry.get('height'),
            'length_m': geometry.get('length'),
        }
        base['material'] = {
            'name': material.get('material_name'),
            'E_Pa': material.get('E'),
            'fy_Pa': material.get('fy'),
        }

        # 荷载
        loads = design_proposal.get('loads', {})
        base['loads'] = {
            'distributed': loads.get('distributed', []),
            'point': loads.get('point', []),
        }

        # 分析结果
        base['analysis'] = {
            'max_displacement_mm': results.get('max_displacement_mm'),
            'max_stress_MPa': results.get('max_stress_MPa'),
            'max_moment_kNm': results.get('max_moment_kNm'),
            'max_shear_kN': results.get('max_shear_kN'),
        }

        # 规范验算
        code_check = analysis_results.get('code_check', {})
        base['code_check'] = {
            'compliant': code_check.get('compliant'),
            'summary': code_check.get('summary'),
            'safety_factors': code_check.get('safety_factors', {}),
        }

        # 评估结果
        if evaluation_report:
            base['evaluation'] = {
                'score': evaluation_report.get('comprehensive_score'),
                'grade': evaluation_report.get('grade'),
                'economy': evaluation_report.get('dimensions', {}).get('economy', {}).get('score'),
                'safety': evaluation_report.get('dimensions', {}).get('safety', {}).get('score'),
                'efficiency': evaluation_report.get('dimensions', {}).get('structural_efficiency', {}).get('score'),
                'sustainability': evaluation_report.get('dimensions', {}).get('sustainability', {}).get('score'),
            }

        # 几何元素（节点列表）
        nodes = analysis_results.get('results', {}).get('detailed_results', {}).get('nodes', [])
        if nodes:
            base['nodes'] = [{'x': n[0], 'y': n[1], 'z': 0.0} for n in nodes]

        # 3D几何体 — Speckle查看器可渲染
        meshes = self._build_geometry(structure_type, design_proposal)
        if meshes:
            base['@displayValue'] = meshes

        return base

    # ------------------------------------------------------------------
    # 几何构建
    # ------------------------------------------------------------------

    def _box_mesh(self, x0: float, y0: float, z0: float,
                  length: float, w: float, h: float):
        """
        沿X轴方向的长方体Mesh。

        顶点布局（8点）：
          底面：0(x0,y0-w/2,z0)  1(x0+L,y0-w/2,z0)
                2(x0+L,y0+w/2,z0) 3(x0,y0+w/2,z0)
          顶面：4-7 同上但 z+h
        """
        from specklepy.objects.geometry import Mesh
        from specklepy.objects.other import RenderMaterial

        hw = w / 2.0
        x1 = x0 + length
        z1 = z0 + h

        verts = [
            x0, y0 - hw, z0,   # 0
            x1, y0 - hw, z0,   # 1
            x1, y0 + hw, z0,   # 2
            x0, y0 + hw, z0,   # 3
            x0, y0 - hw, z1,   # 4
            x1, y0 - hw, z1,   # 5
            x1, y0 + hw, z1,   # 6
            x0, y0 + hw, z1,   # 7
        ]

        # 6个四边形面（逆时针外法线）
        faces = [
            4, 0, 1, 2, 3,   # 底面
            4, 7, 6, 5, 4,   # 顶面
            4, 0, 4, 5, 1,   # 前面 (y-hw)
            4, 3, 2, 6, 7,   # 后面 (y+hw)
            4, 0, 3, 7, 4,   # 左面 (x0)
            4, 1, 5, 6, 2,   # 右面 (x1)
        ]

        mesh = Mesh(vertices=verts, faces=faces, units='m')
        return mesh

    def _vertical_box_mesh(self, x: float, y0: float, z0: float,
                           height: float, w: float, d: float):
        """
        沿Z轴方向的竖向长方体Mesh（柱）。

        w: 截面宽（沿X），d: 截面深（沿Y）
        """
        from specklepy.objects.geometry import Mesh

        hw = w / 2.0
        hd = d / 2.0
        z1 = z0 + height

        verts = [
            x - hw, y0 - hd, z0,   # 0
            x + hw, y0 - hd, z0,   # 1
            x + hw, y0 + hd, z0,   # 2
            x - hw, y0 + hd, z0,   # 3
            x - hw, y0 - hd, z1,   # 4
            x + hw, y0 - hd, z1,   # 5
            x + hw, y0 + hd, z1,   # 6
            x - hw, y0 + hd, z1,   # 7
        ]

        faces = [
            4, 0, 1, 2, 3,
            4, 7, 6, 5, 4,
            4, 0, 4, 5, 1,
            4, 3, 2, 6, 7,
            4, 0, 3, 7, 4,
            4, 1, 5, 6, 2,
        ]

        mesh = Mesh(vertices=verts, faces=faces, units='m')
        return mesh

    def _diagonal_box_mesh(self, x0: float, y0: float, z0: float,
                           x1: float, y1: float, z1: float, size: float):
        """
        创建连接两点的斜向杆件Mesh。

        Args:
            x0, y0, z0: 起点坐标
            x1, y1, z1: 终点坐标
            size: 杆件截面尺寸（正方形截面）
        """
        from specklepy.objects.geometry import Mesh
        import math

        # 计算杆件方向向量
        dx = x1 - x0
        dy = y1 - y0
        dz = z1 - z0
        length = math.sqrt(dx**2 + dy**2 + dz**2)

        if length < 1e-6:
            return None

        # 归一化方向向量
        ux = dx / length
        uy = dy / length
        uz = dz / length

        # 构建局部坐标系（使用简化方法）
        # 找一个垂直于杆件的向量
        if abs(ux) < 0.9:
            vx, vy, vz = 1.0, 0.0, 0.0
        else:
            vx, vy, vz = 0.0, 1.0, 0.0

        # 叉乘得到第一个垂直向量
        wx = uy * vz - uz * vy
        wy = uz * vx - ux * vz
        wz = ux * vy - uy * vx
        w_len = math.sqrt(wx**2 + wy**2 + wz**2)
        wx /= w_len
        wy /= w_len
        wz /= w_len

        # 再次叉乘得到第二个垂直向量
        nx = uy * wz - uz * wy
        ny = uz * wx - ux * wz
        nz = ux * wy - uy * wx

        # 生成8个顶点（矩形截面）
        hs = size / 2.0
        verts = []
        for end_point in [(x0, y0, z0), (x1, y1, z1)]:
            for i in [-1, 1]:
                for j in [-1, 1]:
                    verts.extend([
                        end_point[0] + hs * i * wx + hs * j * nx,
                        end_point[1] + hs * i * wy + hs * j * ny,
                        end_point[2] + hs * i * wz + hs * j * nz
                    ])

        # 定义面（6个四边形面）
        faces = [
            4, 0, 1, 3, 2,   # 起点端面
            4, 4, 6, 7, 5,   # 终点端面
            4, 0, 4, 5, 1,   # 侧面1
            4, 1, 5, 7, 3,   # 侧面2
            4, 3, 7, 6, 2,   # 侧面3
            4, 2, 6, 4, 0,   # 侧面4
        ]

        mesh = Mesh(vertices=verts, faces=faces, units='m')
        return mesh

    def _cylinder_mesh(self, x0: float, y0: float, z0: float,
                       length: float, radius: float, segments: int = 12):
        """沿 X 轴方向的圆柱体 Mesh（桁架水平杆）。"""
        from specklepy.objects.geometry import Mesh
        import math

        verts = []
        for x in (x0, x0 + length):
            for k in range(segments):
                angle = 2 * math.pi * k / segments
                verts.extend([x, y0 + radius * math.cos(angle), z0 + radius * math.sin(angle)])

        faces = []
        # 两端封口
        for start_idx in (0, segments):
            for k in range(1, segments - 1):
                faces.extend([3, start_idx, start_idx + k, start_idx + k + 1])
        # 侧面
        for k in range(segments):
            k_next = (k + 1) % segments
            faces.extend([4, k, k_next, segments + k_next, segments + k])

        return Mesh(vertices=verts, faces=faces, units='m')

    def _vertical_cylinder_mesh(self, x: float, y0: float, z0: float,
                                 height: float, radius: float, segments: int = 12):
        """沿 Z 轴方向的圆柱体 Mesh（桁架竖腹杆）。"""
        from specklepy.objects.geometry import Mesh
        import math

        verts = []
        for z in (z0, z0 + height):
            for k in range(segments):
                angle = 2 * math.pi * k / segments
                verts.extend([x + radius * math.cos(angle), y0 + radius * math.sin(angle), z])

        faces = []
        for start_idx in (0, segments):
            for k in range(1, segments - 1):
                faces.extend([3, start_idx, start_idx + k, start_idx + k + 1])
        for k in range(segments):
            k_next = (k + 1) % segments
            faces.extend([4, k, k_next, segments + k_next, segments + k])

        return Mesh(vertices=verts, faces=faces, units='m')

    def _diagonal_cylinder_mesh(self, x0: float, y0: float, z0: float,
                                 x1: float, y1: float, z1: float,
                                 radius: float, segments: int = 12):
        """连接两点的斜向圆柱体 Mesh（桁架斜腹杆）。"""
        from specklepy.objects.geometry import Mesh
        import math

        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        length = math.sqrt(dx**2 + dy**2 + dz**2)
        if length < 1e-6:
            return None

        ux, uy, uz = dx / length, dy / length, dz / length

        # 构建垂直于轴向的局部坐标系
        ref = (1.0, 0.0, 0.0) if abs(ux) < 0.9 else (0.0, 1.0, 0.0)
        wx = uy * ref[2] - uz * ref[1]
        wy = uz * ref[0] - ux * ref[2]
        wz = ux * ref[1] - uy * ref[0]
        w_len = math.sqrt(wx**2 + wy**2 + wz**2)
        wx, wy, wz = wx / w_len, wy / w_len, wz / w_len
        nx = uy * wz - uz * wy
        ny = uz * wx - ux * wz
        nz = ux * wy - uy * wx

        verts = []
        for end in ((x0, y0, z0), (x1, y1, z1)):
            for k in range(segments):
                angle = 2 * math.pi * k / segments
                c, s = math.cos(angle), math.sin(angle)
                verts.extend([
                    end[0] + radius * (c * wx + s * nx),
                    end[1] + radius * (c * wy + s * ny),
                    end[2] + radius * (c * wz + s * nz),
                ])

        faces = []
        for start_idx in (0, segments):
            for k in range(1, segments - 1):
                faces.extend([3, start_idx, start_idx + k, start_idx + k + 1])
        for k in range(segments):
            k_next = (k + 1) % segments
            faces.extend([4, k, k_next, segments + k_next, segments + k])

        return Mesh(vertices=verts, faces=faces, units='m')

    def _build_geometry(self, structure_type: str, design_proposal: Dict) -> List:
        """根据结构类型分发几何构建。"""
        if structure_type in ('beam', 'cantilever_beam', 'continuous_beam'):
            return self._beam_meshes(design_proposal)
        elif structure_type == 'frame':
            return self._frame_meshes(design_proposal)
        elif structure_type == 'truss':
            return self._truss_meshes(design_proposal)
        return []

    def _beam_meshes(self, design_proposal: Dict) -> List:
        """梁类结构（单根水平长方体）。"""
        geometry = design_proposal.get('geometry', {})
        length = float(geometry.get('length', 5.0))
        width = float(geometry.get('width', 0.3))
        height = float(geometry.get('height', 0.5))
        return [self._box_mesh(0.0, 0.0, 0.0, length, width, height)]

    def _frame_meshes(self, design_proposal: Dict) -> List:
        """框架结构：柱 + 梁。"""
        geometry = design_proposal.get('geometry', {})
        bay_widths = [float(b) for b in geometry.get('bay_widths', [5.0])]
        story_heights = [float(h) for h in geometry.get('story_heights', [3.0])]
        col_w = float(geometry.get('columns', {}).get('width', 0.4))
        col_d = float(geometry.get('columns', {}).get('depth', 0.4))
        beam_w = float(geometry.get('beams', {}).get('width', 0.3))
        beam_d = float(geometry.get('beams', {}).get('depth', 0.5))

        meshes = []

        # 柱X坐标（含首尾节点）
        col_x_positions = [0.0]
        for bw in bay_widths:
            col_x_positions.append(col_x_positions[-1] + bw)

        # 生成柱
        z_base = 0.0
        for sh in story_heights:
            for cx in col_x_positions:
                meshes.append(self._vertical_box_mesh(cx, 0.0, z_base, sh, col_w, col_d))
            z_base += sh

        # 生成梁
        z_base = 0.0
        for sh in story_heights:
            z_top = z_base + sh
            beam_z = z_top - beam_d  # 梁顶齐楼层顶
            x_start = 0.0
            for bw in bay_widths:
                meshes.append(self._box_mesh(x_start, 0.0, beam_z, bw, beam_w, beam_d))
                x_start += bw
            z_base += sh

        return meshes

    def _truss_meshes(self, design_proposal: Dict) -> List:
        """桁架结构：下弦、上弦、腹杆（圆形截面）。"""
        import math
        geometry = design_proposal.get('geometry', {})
        material = design_proposal.get('material', {})
        span = float(geometry.get('span', 10.0))
        height = float(geometry.get('height', 2.0))
        n_panels = int(geometry.get('n_panels', 4))

        # 从截面积 A 反算圆形截面半径，与分析器保持一致；A 缺失时退化为默认值
        A = float(material.get('A', math.pi * 0.05 ** 2))
        radius = math.sqrt(A / math.pi)

        panel_len = span / n_panels
        meshes = []

        # 下弦杆（圆柱）
        for i in range(n_panels):
            meshes.append(self._cylinder_mesh(i * panel_len, 0.0, 0.0, panel_len, radius))

        # 上弦杆（圆柱）
        for i in range(n_panels):
            meshes.append(self._cylinder_mesh(i * panel_len, 0.0, height, panel_len, radius))

        # 竖腹杆（圆柱）
        for i in range(n_panels + 1):
            meshes.append(self._vertical_cylinder_mesh(i * panel_len, 0.0, 0.0, height, radius))

        # 斜腹杆（斜向圆柱）
        for i in range(n_panels):
            x0 = i * panel_len
            x1 = x0 + panel_len
            if i % 2 == 0:
                meshes.append(self._diagonal_cylinder_mesh(x0, 0.0, 0.0, x1, 0.0, height, radius))
            else:
                meshes.append(self._diagonal_cylinder_mesh(x0, 0.0, height, x1, 0.0, 0.0, radius))

        return meshes
