"""
视图函数：处理 API 请求和页面渲染
"""
import os
import time
import tempfile
import shutil
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


@api_view(['POST'])
def download_xapk_file(request):
    """
    下载 XAPK 文件
    
    Request body:
        {
            'url': str  # XAPK 文件的下载地址
        }
    
    Returns:
        Response: {
            'success': bool,
            'message': str,
            'file_path': str,
            'file_name': str,
            'error': str
        }
    """
    url = request.data.get('url')
    
    if not url:
        return Response({
            'success': False,
            'message': '参数不完整',
            'error': '缺少 url 参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 验证 URL 格式
    if not url.startswith(('http://', 'https://')):
        return Response({
            'success': False,
            'message': 'URL 格式错误',
            'error': 'URL 必须以 http:// 或 https:// 开头'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 创建保存目录
    save_dir = os.path.join(settings.MEDIA_ROOT, 'xapk')
    os.makedirs(save_dir, exist_ok=True)
    
    # 先下载到临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xapk', dir=save_dir)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        # 下载文件
        download_result = download_xapk(url, temp_path)
        
        if not download_result['success']:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return Response({
                'success': False,
                'message': download_result['message'],
                'file_path': None,
                'file_name': None,
                'error': download_result['error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 解压并读取 manifest.json 获取 package_name
        extract_dir = tempfile.mkdtemp(dir=settings.TEMP_ROOT)
        try:
            extract_result = extract_xapk(temp_path, extract_dir)
            
            if not extract_result['success'] or not extract_result.get('package_name'):
                # 如果无法获取 package_name，使用默认名称
                package_name = f'downloaded_{os.urandom(8).hex()}'
            else:
                package_name = extract_result['package_name']
            
            # 最终文件路径（以 package_name 命名）
            final_file_name = f'{package_name}.xapk'
            final_file_path = os.path.join(save_dir, final_file_name)
            
            # 如果文件已存在，添加时间戳
            if os.path.exists(final_file_path):
                timestamp = int(time.time())
                final_file_name = f'{package_name}_{timestamp}.xapk'
                final_file_path = os.path.join(save_dir, final_file_name)
            
            # 重命名临时文件为最终文件名
            os.rename(temp_path, final_file_path)
            
            return Response({
                'success': True,
                'message': '下载成功',
                'file_path': final_file_path,
                'file_name': final_file_name,
                'error': None
            })
        finally:
            # 清理临时解压目录
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            # 如果临时文件还存在（重命名失败），删除它
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        # 确保清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return Response({
            'success': False,
            'message': '下载或处理失败',
            'file_path': None,
            'file_name': None,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
