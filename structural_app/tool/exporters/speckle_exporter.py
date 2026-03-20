"""
SpeckleExporter - 将结构设计结果推送到Speckle BIM平台
"""
from typing import Dict, Any, Optional
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

        Returns:
            {'status': 'success', 'url': '...', 'model_id': '...'}
            {'status': 'error', 'error': '...'}
        """
        try:
            from specklepy.objects.base import Base
            from specklepy.transports.server import ServerTransport
            from specklepy.core.api import operations

            client = self._get_client()
            structure_type = design_proposal.get('type', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            model_name = f"{structure_type}_{timestamp}"

            # 创建model
            from specklepy.core.api.inputs.model_inputs import CreateModelInput
            model = client.model.create(
                CreateModelInput(name=model_name, project_id=self.project_id)
            )

            # 构建Base对象
            base = self._build_base_object(design_proposal, analysis_results, evaluation_report)

            # 推送对象
            transport = ServerTransport(client=client, stream_id=self.project_id)
            obj_id = operations.send(base, [transport])

            # 创建version
            from specklepy.core.api.inputs.version_inputs import CreateVersionInput
            client.version.create(
                CreateVersionInput(
                    object_id=obj_id,
                    model_id=model.id,
                    project_id=self.project_id,
                    message=f"{structure_type} 结构设计方案 {timestamp}"
                )
            )

            url = f"{self.server_url}/projects/{self.project_id}/models/{model.id}"
            return {'status': 'success', 'url': url, 'model_id': model.id}

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

        return base
