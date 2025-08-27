import os
import time
import logging
from django.utils import timezone
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from .models import (
    RemoteSensingImage, 
    EcologicalIndex, 
    RSEIResult, 
    ProcessingTask
)
from .ecological_indices import EcologicalIndexCalculator

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def calculate_ecological_indices(self, image_id, indices_list):
    """
    计算生态指数的Celery任务
    
    Args:
        image_id: 遥感影像ID
        indices_list: 要计算的指数列表
    """
    # 初始化变量，确保在finally块中可以访问
    task = None
    image = None
    calculator = None
    
    try:
        logger.info(f"开始执行生态指数计算任务，影像ID: {image_id}")
        logger.info(f"请求的指数列表: {indices_list}")
        logger.info(f"指数列表类型: {type(indices_list)}")
        logger.info(f"指数列表长度: {len(indices_list) if indices_list else 0}")
        
        # 输入验证
        if not image_id:
            raise ValueError("影像ID不能为空")
        
        if not indices_list:
            raise ValueError("指数列表为空，无法进行计算")
        
        if not isinstance(indices_list, (list, tuple)):
            raise ValueError(f"指数列表必须是列表或元组，当前类型: {type(indices_list)}")
        
        if len(indices_list) == 0:
            raise ValueError("指数列表不能为空")
        
        logger.info("输入参数验证通过")
        
        # 获取遥感影像
        try:
            image = RemoteSensingImage.objects.get(id=image_id)
            logger.info(f"成功获取遥感影像: {image.name}")
        except RemoteSensingImage.DoesNotExist:
            raise ValueError(f"找不到ID为 {image_id} 的遥感影像")
        
        # 创建处理任务记录
        task = ProcessingTask.objects.create(
            remote_sensing_image=image,
            task_type='ecological_index_calculation',
            status='processing'
        )
        logger.info(f"创建处理任务成功，任务ID: {task.id}")
        
        # 更新任务进度
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': len(indices_list), 'status': '开始处理...'}
        )
        
        # 初始化计算器
        logger.info(f"开始初始化计算器，影像路径: {image.file_path.path}")
        calculator = EcologicalIndexCalculator(image.file_path.path)
        
        if not calculator.load_image():
            raise Exception("无法加载遥感影像")
        
        logger.info("影像加载成功，开始计算指数")
        
        # 创建输出目录
        output_dir = os.path.join(settings.MEDIA_ROOT, 'ecological_indices', str(image_id))
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"创建输出目录: {output_dir}")
        
        # 定义支持的指数类型和对应的计算方法
        supported_indices = {
            'ndvi': 'calculate_ndvi',
            'ndwi': 'calculate_ndwi', 
            'ndbi': 'calculate_ndbi',
            'ndsi': 'calculate_ndsi',
            'wetness': 'calculate_wetness',
            'dryness': 'calculate_dryness',
            'heat': 'calculate_heat',
            'greenness': 'calculate_greenness'
        }
        
        # 计算各指数
        calculated_indices = {}
        
        for i, index_type in enumerate(indices_list):
            try:
                logger.info(f"开始计算指数 {index_type} ({i+1}/{len(indices_list)})")
                
                # 检查指数类型是否支持
                if index_type not in supported_indices:
                    logger.warning(f"不支持的指数类型: {index_type}，跳过")
                    continue
                
                # 更新进度
                progress = int((i / len(indices_list)) * 100)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i + 1, 
                        'total': len(indices_list), 
                        'status': f'正在计算 {index_type}...'
                    }
                )
                
                # 动态调用计算方法
                method_name = supported_indices[index_type]
                if hasattr(calculator, method_name):
                    method = getattr(calculator, method_name)
                    index_data = method()
                else:
                    logger.warning(f"计算器没有方法: {method_name}")
                    continue
                
                if index_data is None:
                    logger.warning(f"计算 {index_type} 失败，结果为None")
                    continue
                
                logger.info(f"指数 {index_type} 计算成功，开始计算统计信息")
                
                # 计算统计信息
                stats = calculator.calculate_statistics(index_data)
                
                if stats is None:
                    logger.warning(f"指数 {index_type} 统计信息计算失败")
                    continue
                
                logger.info(f"指数 {index_type} 统计信息计算成功")
                
                # 保存结果文件
                result_filename = f"{index_type}_result.tif"
                result_path = os.path.join(output_dir, result_filename)
                if calculator.save_result(index_data, result_path):
                    logger.info(f"指数 {index_type} 结果文件保存成功: {result_path}")
                else:
                    logger.warning(f"指数 {index_type} 结果文件保存失败")
                
                # 创建可视化
                viz_filename = f"{index_type}_visualization.png"
                viz_path = os.path.join(output_dir, viz_filename)
                if calculator.create_visualization(index_data, index_type.upper(), viz_path):
                    logger.info(f"指数 {index_type} 可视化图片创建成功: {viz_path}")
                else:
                    logger.warning(f"指数 {index_type} 可视化图片创建失败")
                
                # 保存到数据库 - 使用安全的字典访问
                try:
                    ecological_index = EcologicalIndex.objects.create(
                        remote_sensing_image=image,
                        index_type=index_type,
                        result_file=f'ecological_indices/{image_id}/{result_filename}',
                        visualization_file=f'ecological_indices/{image_id}/{viz_filename}',
                        min_value=stats.get('min_value'),
                        max_value=stats.get('max_value'),
                        mean_value=stats.get('mean_value'),
                        std_value=stats.get('std_value'),
                        excellent_area=stats.get('excellent_area'),
                        good_area=stats.get('good_area'),
                        moderate_area=stats.get('moderate_area'),
                        poor_area=stats.get('poor_area'),
                        bad_area=stats.get('bad_area'),
                    )
                    
                    calculated_indices[index_type] = ecological_index
                    logger.info(f"指数 {index_type} 数据库记录创建成功，ID: {ecological_index.id}")
                    
                except Exception as db_error:
                    logger.error(f"创建指数 {index_type} 数据库记录失败: {db_error}")
                    continue
                
            except Exception as e:
                logger.error(f"计算指数 {index_type} 时出错: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        logger.info(f"基础指数计算完成，成功计算 {len(calculated_indices)} 个指数")
        
        # 如果计算了RSEI所需的四个分量，则计算RSEI
        rsei_components = ['greenness', 'wetness', 'dryness', 'heat']
        if all(comp in calculated_indices for comp in rsei_components):
            try:
                logger.info("开始计算RSEI...")
                self.update_state(
                    state='PROGRESS',
                    meta={'current': len(indices_list), 'total': len(indices_list) + 1, 'status': '正在计算RSEI...'}
                )
                
                rsei_result = calculator.calculate_rsei()
                if rsei_result:
                    logger.info("RSEI计算成功，开始保存结果")
                    
                    # 保存RSEI结果
                    rsei_filename = "rsei_result.tif"
                    rsei_path = os.path.join(output_dir, rsei_filename)
                    if calculator.save_result(rsei_result.get('rsei'), rsei_path):
                        logger.info(f"RSEI结果文件保存成功: {rsei_path}")
                    else:
                        logger.warning("RSEI结果文件保存失败")
                    
                    # 创建RSEI可视化
                    rsei_viz_filename = "rsei_visualization.png"
                    rsei_viz_path = os.path.join(output_dir, rsei_viz_filename)
                    if calculator.create_visualization(rsei_result.get('rsei'), 'RSEI', rsei_viz_path):
                        logger.info(f"RSEI可视化图片创建成功: {rsei_viz_path}")
                    else:
                        logger.warning("RSEI可视化图片创建失败")
                    
                    # 计算RSEI统计信息
                    rsei_stats = calculator.calculate_statistics(rsei_result.get('rsei'))
                    
                    if rsei_stats is None:
                        logger.warning("RSEI统计信息计算失败")
                    else:
                        logger.info("RSEI统计信息计算成功")
                        
                        # 保存RSEI指数 - 使用安全的字典访问
                        try:
                            rsei_index = EcologicalIndex.objects.create(
                                remote_sensing_image=image,
                                index_type='rsei',
                                result_file=f'ecological_indices/{image_id}/{rsei_filename}',
                                visualization_file=f'ecological_indices/{image_id}/{rsei_viz_filename}',
                                min_value=rsei_stats.get('min_value'),
                                max_value=rsei_stats.get('max_value'),
                                mean_value=rsei_stats.get('mean_value'),
                                std_value=rsei_stats.get('std_value'),
                                excellent_area=rsei_stats.get('excellent_area'),
                                good_area=rsei_stats.get('good_area'),
                                moderate_area=rsei_stats.get('moderate_area'),
                                poor_area=rsei_stats.get('poor_area'),
                                bad_area=rsei_stats.get('bad_area'),
                            )
                            
                            logger.info(f"RSEI指数数据库记录创建成功，ID: {rsei_index.id}")
                            
                            # 创建RSEI结果记录 - 使用安全的字典访问
                            try:
                                RSEIResult.objects.create(
                                    remote_sensing_image=image,
                                    greenness=calculated_indices['greenness'],
                                    wetness=calculated_indices['wetness'],
                                    dryness=calculated_indices['dryness'],
                                    heat=calculated_indices['heat'],
                                    rsei_result=rsei_index,
                                    pc1_variance=rsei_result.get('pca_variance', [0])[0] if rsei_result.get('pca_variance') else 0,
                                    pc2_variance=rsei_result.get('pca_variance', [0, 0])[1] if rsei_result.get('pca_variance') and len(rsei_result.get('pca_variance', [])) > 1 else 0,
                                    pc3_variance=rsei_result.get('pca_variance', [0, 0, 0])[2] if rsei_result.get('pca_variance') and len(rsei_result.get('pca_variance', [])) > 2 else 0,
                                    pc4_variance=rsei_result.get('pca_variance', [0, 0, 0, 0])[3] if rsei_result.get('pca_variance') and len(rsei_result.get('pca_variance', [])) > 3 else 0,
                                    greenness_weight=rsei_result.get('pca_components', [[0, 0, 0, 0]])[0][0] if rsei_result.get('pca_components') and len(rsei_result.get('pca_components', [])) > 0 else 0,
                                    wetness_weight=rsei_result.get('pca_components', [[0, 0, 0, 0]])[0][1] if rsei_result.get('pca_components') and len(rsei_result.get('pca_components', [])) > 0 else 0,
                                    dryness_weight=rsei_result.get('pca_components', [[0, 0, 0, 0]])[0][2] if rsei_result.get('pca_components') and len(rsei_result.get('pca_components', [])) > 0 else 0,
                                    heat_weight=rsei_result.get('pca_components', [[0, 0, 0, 0]])[0][3] if rsei_result.get('pca_components') and len(rsei_result.get('pca_components', [])) > 0 else 0,
                                )
                                
                                logger.info("RSEI结果记录创建成功")
                                
                            except Exception as rsei_db_error:
                                logger.error(f"创建RSEI结果记录失败: {rsei_db_error}")
                        except Exception as rsei_index_error:
                            logger.error(f"创建RSEI指数记录失败: {rsei_index_error}")
                else:
                    logger.warning("RSEI计算失败")
                
            except Exception as e:
                logger.error(f"计算RSEI时出错: {e}")
                import traceback
                traceback.print_exc()
        
        # 更新遥感影像状态
        try:
            image.is_processed = True
            image.processing_status = 'completed'
            image.save()
            logger.info("遥感影像状态更新为完成")
        except Exception as status_error:
            logger.error(f"更新遥感影像状态失败: {status_error}")
        
        # 更新任务状态
        try:
            from django.utils import timezone
            task.status = 'completed'
            task.progress = 100
            task.current_step = '处理完成'
            task.completed_at = timezone.now()
            task.save()
            logger.info("任务状态更新为完成")
        except Exception as task_status_error:
            logger.error(f"更新任务状态失败: {task_status_error}")
        
        logger.info(f"生态指数计算任务完成，成功计算 {len(calculated_indices)} 个指数")
        return {
            'status': 'success',
            'message': f'成功计算 {len(calculated_indices)} 个生态指数',
            'calculated_indices': list(calculated_indices.keys())
        }
        
    except Exception as e:
        logger.error(f"生态指数计算任务失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 更新任务状态为失败
        if task:
            try:
                task.status = 'failed'
                task.error_message = str(e)
                task.save()
                logger.info("任务状态已更新为失败")
            except Exception as task_error:
                logger.error(f"更新任务状态为失败时出错: {task_error}")
        
        # 更新遥感影像状态为失败
        if image:
            try:
                image.processing_status = 'failed'
                image.save()
                logger.info("遥感影像状态已更新为失败")
            except Exception as image_error:
                logger.error(f"更新遥感影像状态为失败时出错: {image_error}")
        
        # 重新抛出异常，让Celery知道任务失败
        raise e
        
    finally:
        # 确保计算器资源始终被关闭
        if calculator:
            try:
                calculator.close()
                logger.info("计算器资源已关闭")
            except Exception as close_error:
                logger.error(f"关闭计算器资源时出错: {close_error}")


@shared_task(bind=True)
def calculate_rsei_only(self, image_id):
    """
    仅计算RSEI的Celery任务
    
    Args:
        image_id: 遥感影像ID
    """
    # 初始化变量，确保在finally块中可以访问
    task = None
    image = None
    calculator = None
    
    try:
        logger.info(f"开始执行RSEI计算任务，影像ID: {image_id}")
        
        # 输入验证
        if not image_id:
            raise ValueError("影像ID不能为空")
        
        logger.info("输入参数验证通过")
        
        # 获取遥感影像
        try:
            image = RemoteSensingImage.objects.get(id=image_id)
            logger.info(f"成功获取遥感影像: {image.name}")
        except RemoteSensingImage.DoesNotExist:
            raise ValueError(f"找不到ID为 {image_id} 的遥感影像")
        
        # 创建处理任务记录
        task = ProcessingTask.objects.create(
            remote_sensing_image=image,
            task_type='rsei_calculation',
            status='processing'
        )
        logger.info(f"创建RSEI处理任务成功，任务ID: {task.id}")
        
        # 初始化计算器
        logger.info(f"开始初始化计算器，影像路径: {image.file_path.path}")
        calculator = EcologicalIndexCalculator(image.file_path.path)
        
        if not calculator.load_image():
            raise Exception("无法加载遥感影像")
        
        logger.info("影像加载成功，开始计算RSEI")
        
        # 创建输出目录
        output_dir = os.path.join(settings.MEDIA_ROOT, 'ecological_indices', str(image_id))
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"创建输出目录: {output_dir}")
        
        # 计算RSEI
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': '正在计算RSEI...'}
        )
        
        rsei_result = calculator.calculate_rsei()
        if not rsei_result:
            raise Exception("RSEI计算失败")
        
        logger.info("RSEI计算成功，开始保存结果")
        
        # 保存RSEI结果 - 使用安全的字典访问
        rsei_filename = "rsei_result.tif"
        rsei_path = os.path.join(output_dir, rsei_filename)
        if calculator.save_result(rsei_result.get('rsei'), rsei_path):
            logger.info(f"RSEI结果文件保存成功: {rsei_path}")
        else:
            logger.warning("RSEI结果文件保存失败")
        
        # 创建RSEI可视化
        rsei_viz_filename = "rsei_visualization.png"
        rsei_viz_path = os.path.join(output_dir, rsei_viz_filename)
        if calculator.create_visualization(rsei_result.get('rsei'), 'RSEI', rsei_viz_path):
            logger.info(f"RSEI可视化图片创建成功: {rsei_viz_path}")
        else:
            logger.warning("RSEI可视化图片创建失败")
        
        # 计算RSEI统计信息
        rsei_stats = calculator.calculate_statistics(rsei_result.get('rsei'))
        
        if rsei_stats is None:
            logger.warning("RSEI统计信息计算失败")
            raise Exception("RSEI统计信息计算失败")
        
        logger.info("RSEI统计信息计算成功")
        
        # 保存RSEI指数 - 使用安全的字典访问
        try:
            rsei_index = EcologicalIndex.objects.create(
                remote_sensing_image=image,
                index_type='rsei',
                result_file=f'ecological_indices/{image_id}/{rsei_filename}',
                visualization_file=f'ecological_indices/{image_id}/{rsei_viz_filename}',
                min_value=rsei_stats.get('min_value'),
                max_value=rsei_stats.get('max_value'),
                mean_value=rsei_stats.get('mean_value'),
                std_value=rsei_stats.get('std_value'),
                excellent_area=rsei_stats.get('excellent_area'),
                good_area=rsei_stats.get('good_area'),
                moderate_area=rsei_stats.get('moderate_area'),
                poor_area=rsei_stats.get('poor_area'),
                bad_area=rsei_stats.get('bad_area'),
            )
            
            logger.info(f"RSEI指数数据库记录创建成功，ID: {rsei_index.id}")
            
        except Exception as rsei_index_error:
            logger.error(f"创建RSEI指数记录失败: {rsei_index_error}")
            raise Exception(f"创建RSEI指数记录失败: {rsei_index_error}")
        
        # 更新任务状态
        try:
            from django.utils import timezone
            task.status = 'completed'
            task.progress = 100
            task.current_step = 'RSEI计算完成'
            task.completed_at = timezone.now()
            task.save()
            logger.info("RSEI任务状态更新为完成")
        except Exception as task_status_error:
            logger.error(f"更新RSEI任务状态失败: {task_status_error}")
        
        logger.info("RSEI计算任务完成")
        return {
            'status': 'success',
            'message': 'RSEI计算完成',
            'rsei_id': str(rsei_index.id)
        }
        
    except Exception as e:
        logger.error(f"RSEI计算任务失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 更新任务状态为失败
        if task:
            try:
                task.status = 'failed'
                task.error_message = str(e)
                task.save()
                logger.info("RSEI任务状态已更新为失败")
            except Exception as task_error:
                logger.error(f"更新RSEI任务状态为失败时出错: {task_error}")
        
        # 重新抛出异常，让Celery知道任务失败
        raise e
        
    finally:
        # 确保计算器资源始终被关闭
        if calculator:
            try:
                calculator.close()
                logger.info("RSEI计算器资源已关闭")
            except Exception as close_error:
                logger.error(f"关闭RSEI计算器资源时出错: {close_error}")


@shared_task
def cleanup_temp_files():
    """清理临时文件的任务"""
    try:
        # 清理超过24小时的临时文件
        import shutil
        from datetime import datetime, timedelta
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        if os.path.exists(temp_dir):
            current_time = datetime.now()
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isfile(item_path):
                    file_time = datetime.fromtimestamp(os.path.getctime(item_path))
                    if current_time - file_time > timedelta(hours=24):
                        os.remove(item_path)
                        logger.info(f"删除临时文件: {item_path}")
                elif os.path.isdir(item_path):
                    dir_time = datetime.fromtimestamp(os.path.getctime(item_path))
                    if current_time - dir_time > timedelta(hours=24):
                        shutil.rmtree(item_path)
                        logger.info(f"删除临时目录: {item_path}")
        
        return {'status': 'success', 'message': '临时文件清理完成'}
        
    except Exception as e:
        logger.error(f"清理临时文件失败: {e}")
        return {'status': 'error', 'message': str(e)} 