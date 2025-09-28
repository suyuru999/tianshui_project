"""
重大工程叠加分析模块
用于分析生态指数文件和生态修复工程文件的叠加影响
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
from django.utils import timezone
from .models import OverlayAnalysisTask, EcologicalIndexFile, EcologicalProjectFile

logger = logging.getLogger(__name__)


class OverlayAnalyzer:
    """叠加分析器"""
    
    def __init__(self, task: OverlayAnalysisTask):
        self.task = task
        self.ecological_index_file = task.ecological_index_file
        self.ecological_project_file = task.ecological_project_file
        
    def analyze(self) -> Dict[str, Any]:
        """执行叠加分析"""
        try:
            # 更新任务状态
            self.task.status = 'processing'
            self.task.started_at = timezone.now()
            self.task.current_step = '开始分析'
            self.task.progress = 10
            self.task.save()
            
            # 步骤1: 解析生态指数数据
            self.task.current_step = '解析生态指数数据'
            self.task.progress = 20
            self.task.save()
            
            ecological_indices = self._parse_ecological_indices()
            
            # 步骤2: 解析工程项目数据
            self.task.current_step = '解析工程项目数据'
            self.task.progress = 40
            self.task.save()
            
            projects = self._parse_projects()
            
            # 步骤3: 执行风险分析
            self.task.current_step = '执行风险分析'
            self.task.progress = 60
            self.task.save()
            
            risk_analysis = self._perform_risk_analysis(ecological_indices, projects)
            
            # 步骤4: 生成监控建议
            self.task.current_step = '生成监控建议'
            self.task.progress = 80
            self.task.save()
            
            monitoring_recommendations = self._generate_monitoring_recommendations(
                ecological_indices, projects, risk_analysis
            )
            
            # 步骤5: 汇总结果
            self.task.current_step = '汇总分析结果'
            self.task.progress = 90
            self.task.save()
            
            results = {
                'ecological_indices': ecological_indices,
                'projects': projects,
                'risk_analysis': risk_analysis,
                'monitoring_recommendations': monitoring_recommendations,
                'analysis_summary': self._generate_summary(risk_analysis),
                'analysis_timestamp': timezone.now().isoformat()
            }
            
            # 完成分析
            self.task.status = 'completed'
            self.task.progress = 100
            self.task.current_step = '分析完成'
            self.task.completed_at = timezone.now()
            self.task.analysis_results = results
            self.task.overall_risk_level = self._determine_overall_risk_level(risk_analysis)
            self.task.save()
            
            return results
            
        except Exception as e:
            logger.error(f"叠加分析失败: {str(e)}")
            self.task.status = 'failed'
            self.task.error_message = str(e)
            self.task.save()
            raise
    
    def _parse_ecological_indices(self) -> Dict[str, Any]:
        """解析生态指数数据"""
        try:
            indices_data = self.ecological_index_file.indices_data
            
            # 如果是字符串，尝试解析为JSON
            if isinstance(indices_data, str):
                indices_data = json.loads(indices_data)
            
            return {
                'filename': self.ecological_index_file.filename,
                'timestamp': indices_data.get('timestamp'),
                'results': indices_data.get('results', {}),
                'summary': indices_data.get('summary', {}),
                'processed_at': self.ecological_index_file.processed_at.isoformat() if self.ecological_index_file.processed_at else None
            }
        except Exception as e:
            raise ValueError(f"解析生态指数数据失败: {str(e)}")
    
    def _parse_projects(self) -> List[Dict[str, Any]]:
        """解析工程项目数据"""
        try:
            geojson_data = self.ecological_project_file.geojson_data
            
            # 如果是字符串，尝试解析为JSON
            if isinstance(geojson_data, str):
                geojson_data = json.loads(geojson_data)
            
            projects = []
            features = geojson_data.get('features', [])
            
            for feature in features:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                
                project = {
                    'id': properties.get('id'),
                    'name': properties.get('name'),
                    'type': properties.get('type'),
                    'area': properties.get('area'),
                    'status': properties.get('status'),
                    'start_date': properties.get('startDate'),
                    'end_date': properties.get('endDate'),
                    'description': properties.get('description'),
                    'geometry_type': geometry.get('type'),
                    'coordinates': geometry.get('coordinates')
                }
                projects.append(project)
            
            return projects
        except Exception as e:
            raise ValueError(f"解析工程项目数据失败: {str(e)}")
    
    def _perform_risk_analysis(self, ecological_indices: Dict[str, Any], projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行风险分析"""
        results = ecological_indices.get('results', {})
        
        # 基础风险评估指标
        risk_factors = {
            'fragmentation_index': results.get('fragmentation_index', 0),
            'fragility_index': results.get('fragility_index', 0),
            'soil_erosion_index': results.get('soil_erosion_index', 0),
            'land_degradation_index': results.get('land_degradation_index', 0),
            'unused_land_proportion': results.get('unused_land_proportion', 0),
            'cultivated_construction_proportion': results.get('cultivated_construction_proportion', 0)
        }
        
        # 计算各项风险等级
        risk_levels = {}
        
        # 生态脆弱性风险
        fragility_risk = self._calculate_fragility_risk(
            risk_factors['fragility_index'],
            risk_factors['fragmentation_index']
        )
        risk_levels['fragility_risk'] = fragility_risk
        
        # 土壤侵蚀风险
        erosion_risk = self._calculate_erosion_risk(
            risk_factors['soil_erosion_index'],
            risk_factors['land_degradation_index']
        )
        risk_levels['erosion_risk'] = erosion_risk
        
        # 土地利用风险
        land_use_risk = self._calculate_land_use_risk(
            risk_factors['unused_land_proportion'],
            risk_factors['cultivated_construction_proportion']
        )
        risk_levels['land_use_risk'] = land_use_risk
        
        # 工程叠加风险
        project_risk = self._calculate_project_risk(projects)
        risk_levels['project_risk'] = project_risk
        
        # 综合风险评估
        overall_risk = self._calculate_overall_risk(risk_levels)
        
        return {
            'risk_factors': risk_factors,
            'risk_levels': risk_levels,
            'overall_risk': overall_risk,
            'risk_details': self._generate_risk_details(risk_levels, projects)
        }
    
    def _calculate_fragility_risk(self, fragility_index: float, fragmentation_index: float) -> Dict[str, Any]:
        """计算生态脆弱性风险"""
        # 综合脆弱性指数
        combined_index = (fragility_index + fragmentation_index) / 2
        
        if combined_index >= 0.7:
            level = 'critical'
            description = '生态系统极度脆弱，急需保护措施'
        elif combined_index >= 0.5:
            level = 'high'
            description = '生态系统脆弱性较高，需要重点关注'
        elif combined_index >= 0.3:
            level = 'medium'
            description = '生态系统脆弱性中等，需要适度保护'
        else:
            level = 'low'
            description = '生态系统相对稳定'
        
        return {
            'level': level,
            'score': combined_index,
            'description': description
        }
    
    def _calculate_erosion_risk(self, erosion_index: float, degradation_index: float) -> Dict[str, Any]:
        """计算土壤侵蚀风险"""
        combined_index = (erosion_index + degradation_index) / 2
        
        if combined_index >= 0.6:
            level = 'critical'
            description = '土壤侵蚀严重，急需治理'
        elif combined_index >= 0.4:
            level = 'high'
            description = '土壤侵蚀风险较高'
        elif combined_index >= 0.2:
            level = 'medium'
            description = '土壤侵蚀风险中等'
        else:
            level = 'low'
            description = '土壤侵蚀风险较低'
        
        return {
            'level': level,
            'score': combined_index,
            'description': description
        }
    
    def _calculate_land_use_risk(self, unused_proportion: float, construction_proportion: float) -> Dict[str, Any]:
        """计算土地利用风险"""
        # 未利用土地比例过高或建设用地比例过高都是风险
        risk_score = max(unused_proportion / 100, construction_proportion / 100)
        
        if risk_score >= 0.5:
            level = 'high'
            description = '土地利用结构不合理'
        elif risk_score >= 0.3:
            level = 'medium'
            description = '土地利用结构需要优化'
        else:
            level = 'low'
            description = '土地利用结构相对合理'
        
        return {
            'level': level,
            'score': risk_score,
            'description': description
        }
    
    def _calculate_project_risk(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算工程项目风险"""
        if not projects:
            return {
                'level': 'low',
                'score': 0,
                'description': '无工程项目'
            }
        
        # 统计不同状态的项目
        status_counts = {}
        for project in projects:
            status = project.get('status', '未知')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 计算风险分数
        total_projects = len(projects)
        ongoing_projects = status_counts.get('进行中', 0)
        planned_projects = status_counts.get('规划中', 0)
        
        # 进行中和规划中的项目越多，风险越高
        risk_score = (ongoing_projects + planned_projects) / total_projects
        
        if risk_score >= 0.7:
            level = 'high'
            description = f'大量工程项目同时进行，可能对生态环境造成叠加影响'
        elif risk_score >= 0.4:
            level = 'medium'
            description = f'多个工程项目进行中，需要协调管理'
        else:
            level = 'low'
            description = f'工程项目数量适中'
        
        return {
            'level': level,
            'score': risk_score,
            'description': description,
            'project_counts': status_counts
        }
    
    def _calculate_overall_risk(self, risk_levels: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """计算综合风险等级"""
        # 风险等级权重
        weights = {
            'fragility_risk': 0.3,
            'erosion_risk': 0.3,
            'land_use_risk': 0.2,
            'project_risk': 0.2
        }
        
        # 风险等级映射
        level_scores = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        
        # 计算加权平均分
        total_score = 0
        for risk_type, weight in weights.items():
            risk_level = risk_levels.get(risk_type, {}).get('level', 'low')
            score = level_scores.get(risk_level, 1)
            total_score += score * weight
        
        # 确定综合风险等级
        if total_score >= 3.5:
            level = 'critical'
            description = '综合风险极高，需要立即采取措施'
        elif total_score >= 2.5:
            level = 'high'
            description = '综合风险较高，需要重点关注'
        elif total_score >= 1.5:
            level = 'medium'
            description = '综合风险中等，需要持续监控'
        else:
            level = 'low'
            description = '综合风险较低，保持现有管理水平'
        
        return {
            'level': level,
            'score': total_score,
            'description': description
        }
    
    def _generate_risk_details(self, risk_levels: Dict[str, Dict[str, Any]], projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成详细风险说明"""
        details = []
        
        for risk_type, risk_info in risk_levels.items():
            if risk_info['level'] in ['high', 'critical']:
                detail = {
                    'risk_type': risk_type,
                    'level': risk_info['level'],
                    'description': risk_info['description'],
                    'recommendations': self._get_risk_recommendations(risk_type, risk_info['level'])
                }
                details.append(detail)
        
        return details
    
    def _get_risk_recommendations(self, risk_type: str, level: str) -> List[str]:
        """获取风险应对建议"""
        recommendations = {
            'fragility_risk': {
                'high': ['加强生态保护区建设', '限制人类活动干扰', '实施生态修复工程'],
                'critical': ['立即停止破坏性活动', '紧急实施生态保护措施', '建立生态监测系统']
            },
            'erosion_risk': {
                'high': ['实施水土保持工程', '加强植被覆盖', '控制坡面径流'],
                'critical': ['紧急实施防护工程', '大规模植树造林', '建设拦沙坝等设施']
            },
            'land_use_risk': {
                'high': ['优化土地利用结构', '合理规划建设用地', '提高土地利用效率'],
                'critical': ['重新规划土地利用', '严格控制建设用地扩张', '实施土地整治工程']
            },
            'project_risk': {
                'high': ['协调各工程项目进度', '加强环境影响评估', '建立统一监管机制'],
                'critical': ['暂停部分工程项目', '重新评估环境影响', '制定综合管理方案']
            }
        }
        
        return recommendations.get(risk_type, {}).get(level, ['加强监测和管理'])
    
    def _generate_monitoring_recommendations(self, ecological_indices: Dict[str, Any], 
                                           projects: List[Dict[str, Any]], 
                                           risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成监控建议"""
        overall_risk = risk_analysis['overall_risk']
        
        # 基础监控建议
        monitoring_plan = {
            'monitoring_frequency': self._determine_monitoring_frequency(overall_risk['level']),
            'key_indicators': self._identify_key_indicators(risk_analysis['risk_levels']),
            'monitoring_areas': self._identify_monitoring_areas(projects, risk_analysis),
            'early_warning_thresholds': self._set_warning_thresholds(ecological_indices['results']),
            'recommended_actions': self._generate_action_plan(risk_analysis)
        }
        
        return monitoring_plan
    
    def _determine_monitoring_frequency(self, risk_level: str) -> str:
        """确定监控频率"""
        frequency_map = {
            'low': '季度监控',
            'medium': '月度监控',
            'high': '周度监控',
            'critical': '日常监控'
        }
        return frequency_map.get(risk_level, '月度监控')
    
    def _identify_key_indicators(self, risk_levels: Dict[str, Dict[str, Any]]) -> List[str]:
        """识别关键监控指标"""
        indicators = []
        
        for risk_type, risk_info in risk_levels.items():
            if risk_info['level'] in ['high', 'critical']:
                if risk_type == 'fragility_risk':
                    indicators.extend(['植被覆盖度', '生物多样性指数', '生态连通性'])
                elif risk_type == 'erosion_risk':
                    indicators.extend(['土壤侵蚀量', '植被覆盖率', '坡面稳定性'])
                elif risk_type == 'land_use_risk':
                    indicators.extend(['土地利用变化', '建设用地扩张', '农田保护'])
                elif risk_type == 'project_risk':
                    indicators.extend(['工程进度', '环境影响', '生态补偿'])
        
        return list(set(indicators))  # 去重
    
    def _identify_monitoring_areas(self, projects: List[Dict[str, Any]], risk_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别重点监控区域"""
        areas = []
        
        # 基于工程项目识别监控区域
        for project in projects:
            if project.get('status') in ['进行中', '规划中']:
                area = {
                    'name': project.get('name'),
                    'type': '工程影响区',
                    'priority': 'high' if project.get('status') == '进行中' else 'medium',
                    'coordinates': project.get('coordinates'),
                    'monitoring_focus': ['工程进度', '环境影响', '生态变化']
                }
                areas.append(area)
        
        return areas
    
    def _set_warning_thresholds(self, current_indices: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """设置预警阈值"""
        thresholds = {}
        
        for indicator, current_value in current_indices.items():
            if indicator in ['fragmentation_index', 'fragility_index', 'soil_erosion_index', 'land_degradation_index']:
                # 对于负面指标，设置上升预警
                thresholds[indicator] = {
                    'yellow_warning': current_value * 1.2,  # 黄色预警：增加20%
                    'red_warning': current_value * 1.5,     # 红色预警：增加50%
                    'current_value': current_value
                }
            elif indicator in ['shannon_diversity', 'cohesion_index']:
                # 对于正面指标，设置下降预警
                thresholds[indicator] = {
                    'yellow_warning': current_value * 0.8,  # 黄色预警：下降20%
                    'red_warning': current_value * 0.6,     # 红色预警：下降40%
                    'current_value': current_value
                }
        
        return thresholds
    
    def _generate_action_plan(self, risk_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成行动计划"""
        actions = []
        
        overall_risk = risk_analysis['overall_risk']
        
        # 基于综合风险等级制定行动计划
        if overall_risk['level'] in ['high', 'critical']:
            actions.append({
                'priority': 'urgent',
                'action': '立即启动应急响应机制',
                'timeline': '1周内',
                'responsible_party': '环境保护部门'
            })
            
            actions.append({
                'priority': 'high',
                'action': '组织专家评估团队',
                'timeline': '2周内',
                'responsible_party': '科研机构'
            })
        
        if overall_risk['level'] in ['medium', 'high', 'critical']:
            actions.append({
                'priority': 'medium',
                'action': '加强监测网络建设',
                'timeline': '1个月内',
                'responsible_party': '监测部门'
            })
        
        actions.append({
            'priority': 'low',
            'action': '定期评估和更新风险分析',
            'timeline': '季度',
            'responsible_party': '管理部门'
        })
        
        return actions
    
    def _generate_summary(self, risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成分析摘要"""
        overall_risk = risk_analysis['overall_risk']
        risk_levels = risk_analysis['risk_levels']
        
        # 统计各风险等级数量
        risk_counts = {}
        for risk_info in risk_levels.values():
            level = risk_info['level']
            risk_counts[level] = risk_counts.get(level, 0) + 1
        
        return {
            'overall_risk_level': overall_risk['level'],
            'overall_risk_score': overall_risk['score'],
            'overall_description': overall_risk['description'],
            'risk_distribution': risk_counts,
            'high_risk_count': risk_counts.get('high', 0) + risk_counts.get('critical', 0),
            'total_risk_factors': len(risk_levels),
            'analysis_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _determine_overall_risk_level(self, risk_analysis: Dict[str, Any]) -> str:
        """确定总体风险等级"""
        return risk_analysis['overall_risk']['level']


def perform_overlay_analysis(task_id: str) -> Dict[str, Any]:
    """执行叠加分析的入口函数"""
    try:
        task = OverlayAnalysisTask.objects.get(id=task_id)
        analyzer = OverlayAnalyzer(task)
        return analyzer.analyze()
    except OverlayAnalysisTask.DoesNotExist:
        raise ValueError(f"分析任务不存在: {task_id}")
    except Exception as e:
        logger.error(f"叠加分析执行失败: {str(e)}")
        raise
