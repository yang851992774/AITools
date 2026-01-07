"""
视图函数：处理 API 请求和页面渲染
"""
import os
import time
import tempfile
import shutil
import threading
import uuid
import re
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    check_adb, check_java, check_device_connected,
    install_apk, install_apks, install_aab, cleanup_temp_files,
    download_xapk, install_xapk, extract_xapk
)

# 存储下载进度的全局字典
download_progress = {}


def index(request):
    """主页面"""
    return render(request, 'installer/index.html')


@api_view(['GET'])
def check_environment(request):
    """
    检查环境（adb 和 java）
    
    Returns:
        JsonResponse: {
            'adb': {...},
            'java': {...}
        }
    """
    adb_status = check_adb()
    java_status = check_java()
    
    return JsonResponse({
        'adb': adb_status,
        'java': java_status
    })


@api_view(['GET'])
def check_device(request):
    """
    检查设备连接
    
    Returns:
        JsonResponse: {
            'connected': bool,
            'devices': list,
            'error': str
        }
    """
    device_status = check_device_connected()
    return JsonResponse(device_status)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_file(request):
    """
    上传文件
    
    Returns:
        Response: {
            'success': bool,
            'message': str,
            'file_path': str,
            'file_name': str,
            'file_type': str,
            'error': str
        }
    """
    if 'file' not in request.FILES:
        return Response({
            'success': False,
            'message': '未选择文件',
            'error': '请选择要上传的文件'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    uploaded_file = request.FILES['file']
    file_name = uploaded_file.name
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # 检查文件类型
    allowed_extensions = ['.apk', '.apks', '.aab', '.xapk']
    if file_ext not in allowed_extensions:
        return Response({
            'success': False,
            'message': '不支持的文件类型',
            'error': f'仅支持 {", ".join(allowed_extensions)} 格式的文件'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 保存文件
    file_type_map = {
        '.apk': 'apk',
        '.apks': 'apks',
        '.aab': 'aab',
        '.xapk': 'xapk'
    }
    file_type = file_type_map[file_ext]
    
    # 创建保存目录
    save_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(save_dir, exist_ok=True)
    
    # 保存文件
    file_path = os.path.join(save_dir, file_name)
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    return Response({
        'success': True,
        'message': '文件上传成功',
        'file_path': file_path,
        'file_name': file_name,
        'file_type': file_type,
        'error': None
    })


@api_view(['POST'])
def install_file(request):
    """
    安装文件
    
    Request body:
        {
            'file_path': str,
            'file_type': str  # 'apk', 'apks', 'aab'
        }
    
    Returns:
        Response: {
            'success': bool,
            'message': str,
            'error': str
        }
    """
    file_path = request.data.get('file_path')
    file_type = request.data.get('file_type')
    
    if not file_path or not file_type:
        return Response({
            'success': False,
            'message': '参数不完整',
            'error': '缺少 file_path 或 file_type 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not os.path.exists(file_path):
        return Response({
            'success': False,
            'message': '文件不存在',
            'error': f'文件路径不存在: {file_path}'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 根据文件类型选择安装方法
    temp_dir = None
    try:
        if file_type == 'apk':
            result = install_apk(file_path)
        elif file_type == 'apks':
            result = install_apks(file_path)
            temp_dir = result.get('temp_dir')
        elif file_type == 'aab':
            result = install_aab(file_path)
            temp_dir = result.get('temp_dir')
        elif file_type == 'xapk':
            result = install_xapk(file_path)
            temp_dir = result.get('temp_dir')
        else:
            return Response({
                'success': False,
                'message': '不支持的文件类型',
                'error': f'不支持的文件类型: {file_type}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 清理临时文件
        if temp_dir:
            cleanup_temp_files(temp_dir)
        
        # 清理上传的文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f'清理上传文件失败: {e}')
        
        return Response(result)
    except Exception as e:
        # 确保清理临时文件
        if temp_dir:
            cleanup_temp_files(temp_dir)
        
        return Response({
            'success': False,
            'message': '安装异常',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _download_xapk_task(task_id, url, temp_path, save_dir):
    """异步下载任务"""
    try:
        # 初始化进度
        download_progress[task_id] = {
            'downloaded': 0,
            'total': 0,
            'speed': 0,
            'status': 'downloading',
            'error': None,
            'file_path': None,
            'file_name': None,
            'start_time': time.time(),
            'last_update_time': time.time(),
            'last_downloaded': 0,
            'speed_samples': []  # 用于计算平均速度的样本
        }
        
        # 进度回调函数
        def progress_callback(downloaded, total):
            current_time = time.time()
            progress_data = download_progress[task_id]
            
            # 更新下载量和总量
            progress_data['downloaded'] = downloaded
            progress_data['total'] = total
            
            # 计算速度（使用滑动窗口平均）
            time_diff = current_time - progress_data['last_update_time']
            
            # 至少间隔 0.5 秒才更新速度，避免频繁计算导致的不准确
            if time_diff >= 0.5:
                downloaded_diff = downloaded - progress_data['last_downloaded']
                if downloaded_diff > 0 and time_diff > 0:
                    # 计算瞬时速度
                    instant_speed = downloaded_diff / time_diff  # bytes per second
                    
                    # 添加到速度样本列表
                    progress_data['speed_samples'].append({
                        'speed': instant_speed,
                        'time': current_time
                    })
                    
                    # 只保留最近5秒内的样本
                    cutoff_time = current_time - 5.0
                    progress_data['speed_samples'] = [
                        s for s in progress_data['speed_samples']
                        if s['time'] >= cutoff_time
                    ]
                    
                    # 计算平均速度（使用最近5秒内的样本）
                    if len(progress_data['speed_samples']) >= 2:
                        # 有足够样本时，使用滑动窗口平均
                        total_speed = sum(s['speed'] for s in progress_data['speed_samples'])
                        avg_speed = total_speed / len(progress_data['speed_samples'])
                        progress_data['speed'] = avg_speed
                    elif len(progress_data['speed_samples']) == 1:
                        # 只有一个样本时，直接使用
                        progress_data['speed'] = instant_speed
                    else:
                        # 没有样本时，使用总平均速度作为后备
                        total_time = current_time - progress_data['start_time']
                        if total_time > 0 and downloaded > 0:
                            progress_data['speed'] = downloaded / total_time
                        else:
                            progress_data['speed'] = instant_speed
                    
                    # 更新最后更新时间
                    progress_data['last_update_time'] = current_time
                    progress_data['last_downloaded'] = downloaded
                elif time_diff >= 2.0:
                    # 如果超过2秒没有新数据，使用总平均速度
                    total_time = current_time - progress_data['start_time']
                    if total_time > 0 and downloaded > 0:
                        progress_data['speed'] = downloaded / total_time
                    else:
                        progress_data['speed'] = 0
                    # 更新最后更新时间，避免频繁计算
                    progress_data['last_update_time'] = current_time
        
        # 下载文件
        download_result = download_xapk(url, temp_path, progress_callback)
        
        if not download_result['success']:
            download_progress[task_id]['status'] = 'error'
            download_progress[task_id]['error'] = download_result['error']
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return
        
        # 解压并读取 manifest.json 获取 package_name
        extract_dir = tempfile.mkdtemp(dir=settings.TEMP_ROOT)
        try:
            extract_result = extract_xapk(temp_path, extract_dir)
            
            if not extract_result['success'] or not extract_result.get('package_name'):
                package_name = f'downloaded_{os.urandom(8).hex()}'
            else:
                package_name = extract_result['package_name']
            
            # 最终文件路径
            final_file_name = f'{package_name}.xapk'
            final_file_path = os.path.join(save_dir, final_file_name)
            
            if os.path.exists(final_file_path):
                timestamp = int(time.time())
                final_file_name = f'{package_name}_{timestamp}.xapk'
                final_file_path = os.path.join(save_dir, final_file_name)
            
            # 重命名临时文件
            os.rename(temp_path, final_file_path)
            
            download_progress[task_id]['status'] = 'completed'
            download_progress[task_id]['file_path'] = final_file_path
            download_progress[task_id]['file_name'] = final_file_name
            download_progress[task_id]['downloaded'] = download_progress[task_id]['total']
        finally:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            if os.path.exists(temp_path) and temp_path != final_file_path:
                os.remove(temp_path)
                
    except Exception as e:
        download_progress[task_id]['status'] = 'error'
        download_progress[task_id]['error'] = str(e)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@api_view(['POST'])
def download_xapk_file(request):
    """
    启动 XAPK 文件下载任务
    
    Request body:
        {
            'url': str,  # XAPK 文件的下载地址（可选）
            'package_name': str  # 应用包名（可选，如果提供则通过包名下载）
        }
    
    Returns:
        Response: {
            'success': bool,
            'task_id': str,
            'message': str,
            'error': str
        }
    """
    url = request.data.get('url')
    package_name = request.data.get('package_name')
    
    # 如果提供了包名，构建下载 URL
    if package_name:
        if not package_name.strip():
            return Response({
                'success': False,
                'task_id': None,
                'message': '参数不完整',
                'error': '包名不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证包名格式
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_.]*$', package_name):
            return Response({
                'success': False,
                'task_id': None,
                'message': '包名格式错误',
                'error': '包名应以字母开头，只能包含字母、数字、点和下划线'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 构建下载 URL
        url = f'https://d.apkpure.com/b/XAPK/{package_name}?version=latest'
    
    # 如果没有 URL 也没有包名，返回错误
    if not url:
        return Response({
            'success': False,
            'task_id': None,
            'message': '参数不完整',
            'error': '缺少 url 或 package_name 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 验证 URL 格式
    if not url.startswith(('http://', 'https://')):
        return Response({
            'success': False,
            'task_id': None,
            'message': 'URL 格式错误',
            'error': 'URL 必须以 http:// 或 https:// 开头'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 创建保存目录
    save_dir = os.path.join(settings.MEDIA_ROOT, 'xapk')
    os.makedirs(save_dir, exist_ok=True)
    
    # 生成任务 ID
    task_id = str(uuid.uuid4())
    
    # 创建临时文件路径
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xapk', dir=save_dir)
    temp_path = temp_file.name
    temp_file.close()
    
    # 启动异步下载任务
    thread = threading.Thread(
        target=_download_xapk_task,
        args=(task_id, url, temp_path, save_dir),
        daemon=True
    )
    thread.start()
    
    return Response({
        'success': True,
        'task_id': task_id,
        'message': '下载任务已启动',
        'error': None
    })


@api_view(['GET'])
def get_download_progress(request):
    """
    获取下载进度
    
    Query params:
        task_id: str  # 任务 ID
    
    Returns:
        Response: {
            'success': bool,
            'downloaded': int,
            'total': int,
            'percent': float,
            'speed': float,  # bytes per second
            'status': str,  # 'downloading', 'completed', 'error'
            'file_path': str,
            'file_name': str,
            'error': str
        }
    """
    task_id = request.query_params.get('task_id')
    
    if not task_id:
        return Response({
            'success': False,
            'error': '缺少 task_id 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if task_id not in download_progress:
        return Response({
            'success': False,
            'error': '任务不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    progress_data = download_progress[task_id]
    
    # 计算百分比
    percent = 0
    if progress_data['total'] > 0:
        percent = (progress_data['downloaded'] / progress_data['total']) * 100
    
    result = {
        'success': True,
        'downloaded': progress_data['downloaded'],
        'total': progress_data['total'],
        'percent': round(percent, 2),
        'speed': progress_data['speed'],
        'status': progress_data['status'],
        'error': progress_data.get('error')
    }
    
    # 如果完成或出错，添加文件信息
    if progress_data['status'] == 'completed':
        result['file_path'] = progress_data['file_path']
        result['file_name'] = progress_data['file_name']
        # 清理进度数据（延迟清理，给前端一些时间获取最终结果）
        def cleanup():
            time.sleep(10)  # 10秒后清理
            if task_id in download_progress:
                del download_progress[task_id]
        threading.Thread(target=cleanup, daemon=True).start()
    elif progress_data['status'] == 'error':
        # 错误时也清理
        def cleanup():
            time.sleep(5)  # 5秒后清理
            if task_id in download_progress:
                del download_progress[task_id]
        threading.Thread(target=cleanup, daemon=True).start()
    
    return Response(result)


@api_view(['POST'])
def install_xapk_file(request):
    """
    安装 XAPK 文件
    
    Request body:
        {
            'file_path': str  # XAPK 文件路径
        }
    
    Returns:
        Response: {
            'success': bool,
            'message': str,
            'error': str
        }
    """
    file_path = request.data.get('file_path')
    
    if not file_path:
        return Response({
            'success': False,
            'message': '参数不完整',
            'error': '缺少 file_path 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not os.path.exists(file_path):
        return Response({
            'success': False,
            'message': '文件不存在',
            'error': f'文件路径不存在: {file_path}'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if not file_path.endswith('.xapk'):
        return Response({
            'success': False,
            'message': '文件类型错误',
            'error': '文件必须是 .xapk 格式'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 安装 XAPK
    temp_dir = None
    try:
        result = install_xapk(file_path)
        temp_dir = result.get('temp_dir')
        
        # 清理临时解压文件（但保留 XAPK 文件）
        if temp_dir:
            cleanup_temp_files(temp_dir)
        
        # 注意：不删除 XAPK 文件，根据需求保留
        return Response({
            'success': result['success'],
            'message': result['message'],
            'error': result.get('error')
        })
    except Exception as e:
        # 确保清理临时文件
        if temp_dir:
            cleanup_temp_files(temp_dir)
        
        return Response({
            'success': False,
            'message': '安装异常',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_xapk_files(request):
    """
    获取已下载的 XAPK 文件列表
    
    Returns:
        Response: {
            'success': bool,
            'files': [
                {
                    'file_name': str,
                    'file_path': str,
                    'file_size': int,
                    'download_time': str,
                    'formatted_size': str
                }
            ],
            'error': str
        }
    """
    try:
        xapk_dir = os.path.join(settings.MEDIA_ROOT, 'xapk')
        os.makedirs(xapk_dir, exist_ok=True)
        
        files = []
        if os.path.exists(xapk_dir):
            for filename in os.listdir(xapk_dir):
                if filename.endswith('.xapk'):
                    file_path = os.path.join(xapk_dir, filename)
                    if os.path.isfile(file_path):
                        file_stat = os.stat(file_path)
                        file_size = file_stat.st_size
                        download_time = datetime.fromtimestamp(file_stat.st_mtime)
                        
                        # 格式化文件大小
                        def format_size(size):
                            for unit in ['B', 'KB', 'MB', 'GB']:
                                if size < 1024.0:
                                    return f"{size:.2f} {unit}"
                                size /= 1024.0
                            return f"{size:.2f} TB"
                        
                        files.append({
                            'file_name': filename,
                            'file_path': file_path,
                            'file_size': file_size,
                            'download_time': download_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'formatted_size': format_size(file_size)
                        })
        
        # 按下载时间倒序排列（最新的在前）
        files.sort(key=lambda x: x['download_time'], reverse=True)
        
        return Response({
            'success': True,
            'files': files,
            'error': None
        })
    except Exception as e:
        return Response({
            'success': False,
            'files': [],
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def delete_xapk_file(request):
    """
    删除 XAPK 文件
    
    Request body:
        {
            'file_path': str  # XAPK 文件路径
        }
    
    Returns:
        Response: {
            'success': bool,
            'message': str,
            'error': str
        }
    """
    file_path = request.data.get('file_path')
    
    if not file_path:
        return Response({
            'success': False,
            'message': '参数不完整',
            'error': '缺少 file_path 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 安全检查：确保文件路径在 xapk 目录下
    xapk_dir = os.path.join(settings.MEDIA_ROOT, 'xapk')
    if not file_path.startswith(xapk_dir):
        return Response({
            'success': False,
            'message': '安全错误',
            'error': '文件路径不在允许的目录中'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if not os.path.exists(file_path):
        return Response({
            'success': False,
            'message': '文件不存在',
            'error': f'文件路径不存在: {file_path}'
        }, status=status.HTTP_404_NOT_FOUND)
    
    try:
        os.remove(file_path)
        return Response({
            'success': True,
            'message': '删除成功',
            'error': None
        })
    except Exception as e:
        return Response({
            'success': False,
            'message': '删除失败',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
