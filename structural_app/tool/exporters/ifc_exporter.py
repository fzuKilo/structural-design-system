"""
IfcExporter - 将结构设计结果导出为 IFC 文件（ifcopenshell）
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import math


class IfcExporter:
    """将 DesignProposal + AnalysisResults + EvaluationReport 导出为 IFC 文件。"""

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: config.toml 中 [ifc] 节的内容，例如：
                output_dir = "outputs/ifc"
                schema    = "IFC4"          # 可选 IFC2X3 / IFC4
        """
        self.output_dir = config.get('output_dir', 'outputs/ifc')
        self.schema = config.get('schema', 'IFC4')

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def export(
        self,
        design_proposal: Dict,
        analysis_results: Dict,
        evaluation_report: Optional[Dict] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        导出结构设计结果为 IFC 文件。

        Returns:
            {'status': 'success', 'path': '...'}
            {'status': 'error',   'error': '...'}
        """
        try:
            import ifcopenshell
            import ifcopenshell.api
            import ifcopenshell.util.element

            structure_type = design_proposal.get('type', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            if filename is None:
                filename = f"{structure_type}_{timestamp}.ifc"

            os.makedirs(self.output_dir, exist_ok=True)
            filepath = os.path.join(self.output_dir, filename)

            model = self._create_ifc_model(
                design_proposal, analysis_results, evaluation_report
            )
            model.write(filepath)

            return {'status': 'success', 'path': os.path.abspath(filepath)}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    # ------------------------------------------------------------------
    # IFC 模型构建
    # ------------------------------------------------------------------

    def _create_ifc_model(
        self,
        design_proposal: Dict,
        analysis_results: Dict,
        evaluation_report: Optional[Dict],
    ):
        import ifcopenshell
        import ifcopenshell.api

        model = ifcopenshell.file(schema=self.schema)

        # --- 项目 / 场地 / 建筑 / 楼层 ---
        project = ifcopenshell.api.run('root.create_entity', model,
                                       ifc_class='IfcProject',
                                       name='StructuralDesignProject')
        ifcopenshell.api.run('unit.assign_unit', model,
                             length={'is_metric': True, 'raw': 'METRES'},
                             area={'is_metric': True, 'raw': 'SQUARE_METRES'},
                             volume={'is_metric': True, 'raw': 'CUBIC_METRES'})

        ctx = ifcopenshell.api.run('context.add_context', model,
                                   context_type='Model')
        body_ctx = ifcopenshell.api.run('context.add_context', model,
                                        context_type='Model',
                                        context_identifier='Body',
                                        target_view='MODEL_VIEW',
                                        parent=ctx)

        site = ifcopenshell.api.run('root.create_entity', model,
                                    ifc_class='IfcSite', name='Site')
        building = ifcopenshell.api.run('root.create_entity', model,
                                        ifc_class='IfcBuilding', name='Building')
        storey = ifcopenshell.api.run('root.create_entity', model,
                                      ifc_class='IfcBuildingStorey', name='Level 1')

        ifcopenshell.api.run('aggregate.assign_object', model,
                             relating_object=project, products=[site])
        ifcopenshell.api.run('aggregate.assign_object', model,
                             relating_object=site, products=[building])
        ifcopenshell.api.run('aggregate.assign_object', model,
                             relating_object=building, products=[storey])

        # --- 属性集：分析结果 ---
        self._add_analysis_pset(model, project, analysis_results)

        # --- 属性集：评估报告 ---
        if evaluation_report:
            self._add_evaluation_pset(model, project, evaluation_report)

        # --- 结构构件 ---
        structure_type = design_proposal.get('type', 'unknown')
        elements = self._build_elements(
            model, body_ctx, storey, structure_type, design_proposal
        )

        # --- 材料 ---
        material_info = design_proposal.get('material', {})
        if material_info and elements:
            self._assign_material(model, elements, material_info)

        return model

    # ------------------------------------------------------------------
    # 属性集
    # ------------------------------------------------------------------

    def _add_analysis_pset(self, model, entity, analysis_results: Dict):
        import ifcopenshell.api

        results = analysis_results.get('results', {})
        code_check = analysis_results.get('code_check', {})

        props = {
            'MaxDisplacement_mm': str(results.get('max_displacement_mm', '')),
            'MaxStress_MPa':      str(results.get('max_stress_MPa', '')),
            'MaxMoment_kNm':      str(results.get('max_moment_kNm', '')),
            'MaxShear_kN':        str(results.get('max_shear_kN', '')),
            'CodeCompliant':      str(code_check.get('compliant', '')),
            'CodeSummary':        str(code_check.get('summary', '')),
        }
        pset = ifcopenshell.api.run('pset.add_pset', model,
                                    product=entity,
                                    name='Pset_StructuralAnalysis')
        ifcopenshell.api.run('pset.edit_pset', model,
                             pset=pset, properties=props)

    def _add_evaluation_pset(self, model, entity, evaluation_report: Dict):
        import ifcopenshell.api

        dims = evaluation_report.get('dimensions', {})
        props = {
            'Score':         str(evaluation_report.get('comprehensive_score', '')),
            'Grade':         str(evaluation_report.get('grade', '')),
            'Economy':       str(dims.get('economy', {}).get('score', '')),
            'Safety':        str(dims.get('safety', {}).get('score', '')),
            'Efficiency':    str(dims.get('structural_efficiency', {}).get('score', '')),
            'Sustainability': str(dims.get('sustainability', {}).get('score', '')),
        }
        pset = ifcopenshell.api.run('pset.add_pset', model,
                                    product=entity,
                                    name='Pset_StructuralEvaluation')
        ifcopenshell.api.run('pset.edit_pset', model,
                             pset=pset, properties=props)

    # ------------------------------------------------------------------
    # 构件分发
    # ------------------------------------------------------------------

    def _build_elements(
        self,
        model,
        body_ctx,
        storey,
        structure_type: str,
        design_proposal: Dict,
    ) -> List:
        if structure_type in ('beam', 'cantilever_beam', 'continuous_beam'):
            return self._build_beams(model, body_ctx, storey, design_proposal)
        elif structure_type == 'frame':
            return self._build_frame(model, body_ctx, storey, design_proposal)
        elif structure_type == 'truss':
            return self._build_truss(model, body_ctx, storey, design_proposal)
        return []

    # ------------------------------------------------------------------
    # 梁
    # ------------------------------------------------------------------

    def _build_beams(self, model, body_ctx, storey, design_proposal: Dict) -> List:
        geometry = design_proposal.get('geometry', {})
        length = float(geometry.get('length', 5.0))
        width  = float(geometry.get('width',  0.3))
        height = float(geometry.get('height', 0.5))

        beam = self._create_beam_member(
            model, body_ctx, storey,
            name='Beam-1',
            x0=0.0, y0=0.0, z0=0.0,
            length=length, width=width, height=height,
        )
        return [beam]

    # ------------------------------------------------------------------
    # 框架
    # ------------------------------------------------------------------

    def _build_frame(self, model, body_ctx, storey, design_proposal: Dict) -> List:
        geometry = design_proposal.get('geometry', {})
        bay_widths    = [float(b) for b in geometry.get('bay_widths', [5.0])]
        story_heights = [float(h) for h in geometry.get('story_heights', [3.0])]
        col_w  = float(geometry.get('columns', {}).get('width', 0.4))
        col_d  = float(geometry.get('columns', {}).get('depth', 0.4))
        beam_w = float(geometry.get('beams',   {}).get('width', 0.3))
        beam_d = float(geometry.get('beams',   {}).get('depth', 0.5))

        col_x = [0.0]
        for bw in bay_widths:
            col_x.append(col_x[-1] + bw)

        elements = []
        z_base = 0.0
        for story_idx, sh in enumerate(story_heights):
            # 柱
            for ci, cx in enumerate(col_x):
                col = self._create_column_member(
                    model, body_ctx, storey,
                    name=f'Col-S{story_idx+1}-{ci+1}',
                    x=cx, y=0.0, z_base=z_base,
                    height=sh, width=col_w, depth=col_d,
                )
                elements.append(col)
            # 梁
            x_start = 0.0
            beam_z = z_base + sh - beam_d
            for bi, bw in enumerate(bay_widths):
                beam = self._create_beam_member(
                    model, body_ctx, storey,
                    name=f'Beam-S{story_idx+1}-B{bi+1}',
                    x0=x_start, y0=0.0, z0=beam_z,
                    length=bw, width=beam_w, height=beam_d,
                )
                elements.append(beam)
                x_start += bw
            z_base += sh

        return elements

    # ------------------------------------------------------------------
    # 桁架
    # ------------------------------------------------------------------

    def _build_truss(self, model, body_ctx, storey, design_proposal: Dict) -> List:
        geometry  = design_proposal.get('geometry', {})
        span      = float(geometry.get('span', 10.0))
        height    = float(geometry.get('height', 2.0))
        n_panels  = int(geometry.get('n_panels', 4))
        bar_size  = 0.1

        panel_len = span / n_panels
        elements  = []

        # 下弦
        for i in range(n_panels):
            m = self._create_beam_member(
                model, body_ctx, storey,
                name=f'BottomChord-{i+1}',
                x0=i * panel_len, y0=0.0, z0=0.0,
                length=panel_len, width=bar_size, height=bar_size,
            )
            elements.append(m)

        # 上弦
        for i in range(n_panels):
            m = self._create_beam_member(
                model, body_ctx, storey,
                name=f'TopChord-{i+1}',
                x0=i * panel_len, y0=0.0, z0=height,
                length=panel_len, width=bar_size, height=bar_size,
            )
            elements.append(m)

        # 竖腹杆
        for i in range(n_panels + 1):
            m = self._create_column_member(
                model, body_ctx, storey,
                name=f'Vertical-{i+1}',
                x=i * panel_len, y=0.0, z_base=0.0,
                height=height, width=bar_size, depth=bar_size,
            )
            elements.append(m)

        # 斜腹杆（用水平梁近似）
        for i in range(n_panels):
            z0 = 0.0 if i % 2 == 0 else height
            m = self._create_beam_member(
                model, body_ctx, storey,
                name=f'Diagonal-{i+1}',
                x0=i * panel_len, y0=0.0, z0=z0,
                length=panel_len, width=bar_size, height=bar_size,
            )
            elements.append(m)

        return elements

    # ------------------------------------------------------------------
    # 低级几何辅助
    # ------------------------------------------------------------------

    def _create_beam_member(
        self, model, body_ctx, storey,
        name: str,
        x0: float, y0: float, z0: float,
        length: float, width: float, height: float,
    ):
        """创建沿 X 轴方向的 IfcBeam（矩形截面拉伸体）。"""
        import ifcopenshell.api

        beam = ifcopenshell.api.run('root.create_entity', model,
                                    ifc_class='IfcBeam', name=name)
        ifcopenshell.api.run('spatial.assign_container', model,
                             relating_structure=storey, products=[beam])

        # 截面轮廓（YZ平面矩形）
        profile = model.createIfcRectangleProfileDef(
            'AREA', None,
            model.createIfcAxis2Placement2D(
                model.createIfcCartesianPoint([0.0, height / 2.0])
            ),
            width, height,
        )

        # 拉伸方向：沿 X
        extrusion_dir = model.createIfcDirection([1.0, 0.0, 0.0])
        placement_2d = model.createIfcAxis2Placement2D(
            model.createIfcCartesianPoint([0.0, 0.0])
        )
        # 截面放置在构件局部坐标的 YZ 平面
        axis_placement = model.createIfcAxis2Placement3D(
            model.createIfcCartesianPoint([0.0, 0.0, 0.0]),
            model.createIfcDirection([0.0, 0.0, 1.0]),
            model.createIfcDirection([1.0, 0.0, 0.0]),
        )
        solid = model.createIfcExtrudedAreaSolid(
            profile, axis_placement, extrusion_dir, length
        )

        shape_rep = model.createIfcShapeRepresentation(
            body_ctx, 'Body', 'SweptSolid', [solid]
        )
        prod_def = model.createIfcProductDefinitionShape(
            None, None, [shape_rep]
        )

        # 世界坐标放置
        location = model.createIfcCartesianPoint([x0, y0, z0])
        local_placement = model.createIfcLocalPlacement(
            None,
            model.createIfcAxis2Placement3D(
                location,
                model.createIfcDirection([0.0, 0.0, 1.0]),
                model.createIfcDirection([1.0, 0.0, 0.0]),
            )
        )
        beam.ObjectPlacement = local_placement
        beam.Representation = prod_def

        return beam

    def _create_column_member(
        self, model, body_ctx, storey,
        name: str,
        x: float, y: float, z_base: float,
        height: float, width: float, depth: float,
    ):
        """创建沿 Z 轴方向的 IfcColumn（矩形截面拉伸体）。"""
        import ifcopenshell.api

        col = ifcopenshell.api.run('root.create_entity', model,
                                   ifc_class='IfcColumn', name=name)
        ifcopenshell.api.run('spatial.assign_container', model,
                             relating_structure=storey, products=[col])

        profile = model.createIfcRectangleProfileDef(
            'AREA', None,
            model.createIfcAxis2Placement2D(
                model.createIfcCartesianPoint([0.0, 0.0])
            ),
            width, depth,
        )

        extrusion_dir = model.createIfcDirection([0.0, 0.0, 1.0])
        axis_placement = model.createIfcAxis2Placement3D(
            model.createIfcCartesianPoint([0.0, 0.0, 0.0]),
            model.createIfcDirection([0.0, 0.0, 1.0]),
            model.createIfcDirection([1.0, 0.0, 0.0]),
        )
        solid = model.createIfcExtrudedAreaSolid(
            profile, axis_placement, extrusion_dir, height
        )

        shape_rep = model.createIfcShapeRepresentation(
            body_ctx, 'Body', 'SweptSolid', [solid]
        )
        prod_def = model.createIfcProductDefinitionShape(
            None, None, [shape_rep]
        )

        location = model.createIfcCartesianPoint([x, y, z_base])
        local_placement = model.createIfcLocalPlacement(
            None,
            model.createIfcAxis2Placement3D(
                location,
                model.createIfcDirection([0.0, 0.0, 1.0]),
                model.createIfcDirection([1.0, 0.0, 0.0]),
            )
        )
        col.ObjectPlacement = local_placement
        col.Representation = prod_def

        return col

    # ------------------------------------------------------------------
    # 材料
    # ------------------------------------------------------------------

    def _assign_material(self, model, elements: List, material_info: Dict):
        import ifcopenshell.api

        mat_name = material_info.get('material_name', 'Concrete')
        material = ifcopenshell.api.run('material.add_material', model,
                                        name=mat_name)

        # 附加弹性属性
        E  = material_info.get('E')
        fy = material_info.get('fy')
        if E or fy:
            props = {}
            if E:
                props['YoungModulus'] = float(E)
            if fy:
                props['YieldStress'] = float(fy)
            pset = ifcopenshell.api.run('pset.add_pset', model,
                                        product=material,
                                        name='Pset_MaterialMechanical')
            ifcopenshell.api.run('pset.edit_pset', model,
                                 pset=pset, properties={k: str(v) for k, v in props.items()})

        # 一次性分配材料给所有元素（更高效）
        ifcopenshell.api.run('material.assign_material', model,
                             products=elements, material=material)
