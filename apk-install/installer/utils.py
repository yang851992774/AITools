"""
工具函数：用于检测环境和执行安装操作
"""
import subprocess
import os
import shutil
import zipfile
import tempfile
import json
import urllib.request
from pathlib import Path
from django.conf import settings


def check_command(command, version_flag='--version'):
    """
    检查命令是否可用
    
    Args:
        command: 要检查的命令
        version_flag: 版本标志参数
    
    Returns:
        dict: {'available': bool, 'version': str, 'error': str}
    """
    try:
        result = subprocess.run(
            [command, version_flag],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            return {
                'available': True,
                'version': version,
                'error': None
            }
        else:
            return {
                'available': False,
                'version': None,
                'error': result.stderr.strip() or '命令执行失败'
            }
    except FileNotFoundError:
        return {
            'available': False,
            'version': None,
            'error': f'未找到命令: {command}'
        }
    except subprocess.TimeoutExpired:
        return {
            'available': False,
            'version': None,
            'error': '命令执行超时'
        }
    except Exception as e:
        return {
            'available': False,
            'version': None,
            'error': str(e)
        }


def check_adb():
    """检查 adb 环境"""
    return check_command('adb', 'version')


def check_java():
    """检查 java 环境"""
    return check_command('java', '-version')


def check_device_connected():
    """
    检查是否有设备连接
    
    Returns:
        dict: {'connected': bool, 'devices': list, 'error': str}
    """
    try:
        result = subprocess.run(
            ['adb', 'devices'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {
                'connected': False,
                'devices': [],
                'error': result.stderr.strip() or 'adb devices 执行失败'
            }
        
        # 解析设备列表
        lines = result.stdout.strip().split('\n')[1:]  # 跳过第一行 "List of devices attached"
        devices = []
        for line in lines:
            if line.strip() and '\t' in line:
                device_id, status = line.strip().split('\t')
                if status == 'device':  # 只返回已授权的设备
                    devices.append(device_id)
        
        return {
            'connected': len(devices) > 0,
            'devices': devices,
            'error': None if devices else '未检测到已连接的设备'
        }
    except FileNotFoundError:
        return {
            'connected': False,
            'devices': [],
            'error': 'adb 命令未找到'
        }
    except subprocess.TimeoutExpired:
        return {
            'connected': False,
            'devices': [],
            'error': '检查设备连接超时'
        }
    except Exception as e:
        return {
            'connected': False,
            'devices': [],
            'error': str(e)
        }


def install_apk(apk_path):
    """
    安装 APK 文件
    
    Args:
        apk_path: APK 文件路径
    
    Returns:
        dict: {'success': bool, 'message': str, 'error': str}
    """
    try:
        result = subprocess.run(
            ['adb', 'install', '-r', apk_path],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            return {
                'success': True,
                'message': '安装成功',
                'error': None
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return {
                'success': False,
                'message': '安装失败',
                'error': error_msg
            }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'message': '安装超时',
            'error': '安装过程超过5分钟'
        }
    except Exception as e:
        return {
            'success': False,
            'message': '安装异常',
            'error': str(e)
        }


def install_apks(apks_path):
    """
    安装 APKS 文件（需要先解压）
    
    Args:
        apks_path: APKS 文件路径
    
    Returns:
        dict: {'success': bool, 'message': str, 'error': str, 'temp_dir': str}
    """
    temp_dir = None
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(dir=settings.TEMP_ROOT)
        
        # 解压 APKS 文件
        with zipfile.ZipFile(apks_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 查找 APK 文件（通常在 splits 目录下）
        splits_dir = os.path.join(temp_dir, 'splits')
        if os.path.exists(splits_dir):
            # 查找 base.apk
            base_apk = os.path.join(splits_dir, 'base.apk')
            if os.path.exists(base_apk):
                # 对于 split APKs，需要使用 install-multiple
                apk_files = [os.path.join(splits_dir, f) for f in os.listdir(splits_dir) if f.endswith('.apk')]
                apk_files.sort()  # 确保 base.apk 在前
                
                # 使用 install-multiple 安装
                cmd = ['adb', 'install-multiple'] + apk_files
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    return {
                        'success': True,
                        'message': '安装成功',
                        'error': None,
                        'temp_dir': temp_dir
                    }
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    return {
                        'success': False,
                        'message': '安装失败',
                        'error': error_msg,
                        'temp_dir': temp_dir
                    }
            else:
                return {
                    'success': False,
                    'message': '未找到 base.apk',
                    'error': 'APKS 文件格式不正确',
                    'temp_dir': temp_dir
                }
        else:
            # 如果没有 splits 目录，尝试直接查找 APK 文件
            apk_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.apk'):
                        apk_files.append(os.path.join(root, file))
            
            if apk_files:
                # 如果只有一个 APK，直接安装
                if len(apk_files) == 1:
                    return install_apk(apk_files[0])
                else:
                    # 多个 APK，使用 install-multiple
                    apk_files.sort()
                    cmd = ['adb', 'install-multiple'] + apk_files
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        return {
                            'success': True,
                            'message': '安装成功',
                            'error': None,
                            'temp_dir': temp_dir
                        }
                    else:
                        error_msg = result.stderr.strip() or result.stdout.strip()
                        return {
                            'success': False,
                            'message': '安装失败',
                            'error': error_msg,
                            'temp_dir': temp_dir
                        }
            else:
                return {
                    'success': False,
                    'message': '未找到 APK 文件',
                    'error': 'APKS 文件格式不正确',
                    'temp_dir': temp_dir
                }
    except zipfile.BadZipFile:
        return {
            'success': False,
            'message': '文件格式错误',
            'error': 'APKS 文件不是有效的 ZIP 文件',
            'temp_dir': temp_dir
        }
    except Exception as e:
        return {
            'success': False,
            'message': '安装异常',
            'error': str(e),
            'temp_dir': temp_dir
        }


def install_aab(aab_path):
    """
    安装 AAB 文件（需要先转换为 APKS，然后安装）
    
    Args:
        aab_path: AAB 文件路径
    
    Returns:
        dict: {'success': bool, 'message': str, 'error': str, 'temp_dir': str, 'apks_path': str}
    """
    temp_dir = None
    apks_path = None
    try:
        # 检查 bundletool 是否可用
        bundletool_check = check_command('bundletool')
        if not bundletool_check['available']:
            # 尝试使用 java -jar bundletool.jar
            bundletool_jar = str(Path(settings.BASE_DIR) / 'bundletool.jar')
            if not os.path.exists(bundletool_jar):
                return {
                    'success': False,
                    'message': 'bundletool 未找到',
                    'error': '请确保 bundletool.jar 存在于项目根目录，或 bundletool 命令可用',
                    'temp_dir': None,
                    'apks_path': None
                }
            bundletool_cmd = ['java', '-jar', bundletool_jar]
        else:
            bundletool_cmd = ['bundletool']
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(dir=settings.TEMP_ROOT)
        apks_path = os.path.join(temp_dir, 'output.apks')
        
        # 使用 bundletool 将 AAB 转换为 APKS
        # 需要生成一个 keystore（可以使用临时密钥）
        keystore_path = os.path.join(temp_dir, 'temp.keystore')
        
        # 生成临时 keystore（如果不存在）
        if not os.path.exists(keystore_path):
            subprocess.run(
                [
                    'keytool', '-genkey', '-v',
                    '-keystore', keystore_path,
                    '-alias', 'temp',
                    '-keyalg', 'RSA',
                    '-keysize', '2048',
                    '-validity', '10000',
                    '-storepass', 'android',
                    '-keypass', 'android',
                    '-dname', 'CN=Android, OU=Android, O=Android, L=Unknown, ST=Unknown, C=US'
                ],
                input='android\n',
                text=True,
                capture_output=True,
                timeout=30
            )
        
        # 构建 bundletool 命令
        build_apks_cmd = bundletool_cmd + [
            'build-apks',
            '--bundle', aab_path,
            '--output', apks_path,
            '--ks', keystore_path,
            '--ks-pass', 'pass:android',
            '--ks-key-alias', 'temp',
            '--key-pass', 'pass:android'
        ]
        
        result = subprocess.run(
            build_apks_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            return {
                'success': False,
                'message': 'AAB 转换失败',
                'error': result.stderr.strip() or result.stdout.strip(),
                'temp_dir': temp_dir,
                'apks_path': None
            }
        
        # 转换成功后，安装 APKS
        install_result = install_apks(apks_path)
        install_result['temp_dir'] = temp_dir
        install_result['apks_path'] = apks_path
        return install_result
        
    except FileNotFoundError as e:
        return {
            'success': False,
            'message': '工具未找到',
            'error': f'未找到必要的工具: {str(e)}',
            'temp_dir': temp_dir,
            'apks_path': apks_path
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'message': '转换超时',
            'error': 'AAB 转换过程超过5分钟',
            'temp_dir': temp_dir,
            'apks_path': apks_path
        }
    except Exception as e:
        return {
            'success': False,
            'message': '安装异常',
            'error': str(e),
            'temp_dir': temp_dir,
            'apks_path': apks_path
        }


def cleanup_temp_files(temp_dir):
    """
    清理临时文件
    
    Args:
        temp_dir: 临时目录路径
    """
    try:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        # 记录错误但不抛出异常
        print(f'清理临时文件失败: {e}')


def download_xapk(url, save_path, progress_callback=None):
    """
    下载 XAPK 文件
    
    Args:
        url: XAPK 文件的下载地址
        save_path: 保存路径
        progress_callback: 进度回调函数，接收 (downloaded, total) 参数
    
    Returns:
        dict: {'success': bool, 'message': str, 'file_path': str, 'error': str}
    """
    try:
        # 确保保存目录存在
        save_dir = os.path.dirname(save_path)
        os.makedirs(save_dir, exist_ok=True)
        
        # 使用流式下载以支持进度回调
        response = urllib.request.urlopen(url)
        total_size = int(response.headers.get('Content-Length', 0))
        
        downloaded = 0
        chunk_size = 8192  # 8KB chunks
        
        with open(save_path, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                
                # 调用进度回调
                if progress_callback and total_size > 0:
                    progress_callback(downloaded, total_size)
        
        return {
            'success': True,
            'message': '下载成功',
            'file_path': save_path,
            'error': None
        }
    except urllib.error.URLError as e:
        return {
            'success': False,
            'message': '下载失败',
            'file_path': None,
            'error': f'URL 错误: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'message': '下载异常',
            'file_path': None,
            'error': str(e)
        }


def extract_xapk(xapk_path, extract_dir):
    """
    解压 XAPK 文件并读取 manifest.json
    
    Args:
        xapk_path: XAPK 文件路径
        extract_dir: 解压目录
    
    Returns:
        dict: {
            'success': bool,
            'manifest': dict,
            'package_name': str,
            'apk_files': list,
            'error': str
        }
    """
    try:
        # 创建解压目录
        os.makedirs(extract_dir, exist_ok=True)
        
        # 解压 XAPK 文件
        with zipfile.ZipFile(xapk_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 读取 manifest.json
        manifest_path = os.path.join(extract_dir, 'manifest.json')
        if not os.path.exists(manifest_path):
            return {
                'success': False,
                'manifest': None,
                'package_name': None,
                'apk_files': [],
                'error': '未找到 manifest.json 文件'
            }
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        package_name = manifest.get('package_name')
        if not package_name:
            return {
                'success': False,
                'manifest': manifest,
                'package_name': None,
                'apk_files': [],
                'error': 'manifest.json 中未找到 package_name'
            }
        
        # 查找所有 APK 文件
        apk_files = []
        
        # 主 APK 文件（package_name.apk）
        main_apk = os.path.join(extract_dir, f'{package_name}.apk')
        if os.path.exists(main_apk):
            apk_files.append(main_apk)
        
        # 查找 split APKs（从 manifest.json 中获取）
        split_apks = manifest.get('split_apks', [])
        # 按照 id 排序，确保 base 在前
        split_apks_sorted = sorted(split_apks, key=lambda x: (x.get('id') != 'base', x.get('id', '')))
        
        for split_apk in split_apks_sorted:
            apk_file = split_apk.get('file')
            if apk_file:
                apk_path = os.path.join(extract_dir, apk_file)
                if os.path.exists(apk_path) and apk_path not in apk_files:
                    # 如果主 APK 已添加，将 split APKs 添加到后面
                    if main_apk in apk_files:
                        apk_files.append(apk_path)
                    else:
                        # 如果主 APK 不存在，检查是否是 base
                        if split_apk.get('id') == 'base':
                            apk_files.insert(0, apk_path)
                        else:
                            apk_files.append(apk_path)
        
        # 如果没找到任何 APK，尝试查找所有 .apk 文件
        if not apk_files:
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.apk'):
                        apk_path = os.path.join(root, file)
                        if apk_path not in apk_files:
                            apk_files.append(apk_path)
        
        return {
            'success': True,
            'manifest': manifest,
            'package_name': package_name,
            'apk_files': apk_files,
            'error': None
        }
    except zipfile.BadZipFile:
        return {
            'success': False,
            'manifest': None,
            'package_name': None,
            'apk_files': [],
            'error': 'XAPK 文件不是有效的 ZIP 文件'
        }
    except json.JSONDecodeError as e:
        return {
            'success': False,
            'manifest': None,
            'package_name': None,
            'apk_files': [],
            'error': f'manifest.json 解析失败: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'manifest': None,
            'package_name': None,
            'apk_files': [],
            'error': str(e)
        }


def install_xapk(xapk_path):
    """
    安装 XAPK 文件
    
    Args:
        xapk_path: XAPK 文件路径
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'error': str,
            'temp_dir': str,
            'xapk_path': str  # 保留的 XAPK 文件路径
        }
    """
    temp_dir = None
    try:
        # 创建临时解压目录
        temp_dir = tempfile.mkdtemp(dir=settings.TEMP_ROOT)
        
        # 解压 XAPK 文件
        extract_result = extract_xapk(xapk_path, temp_dir)
        
        if not extract_result['success']:
            return {
                'success': False,
                'message': '解压失败',
                'error': extract_result['error'],
                'temp_dir': temp_dir,
                'xapk_path': xapk_path
            }
        
        apk_files = extract_result['apk_files']
        if not apk_files:
            return {
                'success': False,
                'message': '未找到 APK 文件',
                'error': 'XAPK 文件中未找到可安装的 APK 文件',
                'temp_dir': temp_dir,
                'xapk_path': xapk_path
            }
        
        # 安装 APK 文件
        if len(apk_files) == 1:
            # 单个 APK，直接安装
            result = install_apk(apk_files[0])
        else:
            # 多个 APK，使用 install-multiple
            # apk_files 已经在 extract_xapk 中按正确顺序排列（主 APK 在前）
            cmd = ['adb', 'install-multiple'] + apk_files
            install_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if install_result.returncode == 0:
                result = {
                    'success': True,
                    'message': '安装成功',
                    'error': None
                }
            else:
                error_msg = install_result.stderr.strip() or install_result.stdout.strip()
                result = {
                    'success': False,
                    'message': '安装失败',
                    'error': error_msg
                }
        
        # 返回结果，注意保留 xapk_path
        result['temp_dir'] = temp_dir
        result['xapk_path'] = xapk_path
        return result
        
    except Exception as e:
        return {
            'success': False,
            'message': '安装异常',
            'error': str(e),
            'temp_dir': temp_dir,
            'xapk_path': xapk_path
        }

