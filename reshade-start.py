import os
import sys
import subprocess
import time
import ctypes
import threading
import zipfile
import shutil
import re
from pathlib import Path

# 导入tkinter但只在需要时初始化
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    TKINTER_AVAILABLE = True
    
    # 设置高DPI兼容性
    if hasattr(ctypes, 'windll'):
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    
except ImportError:
    TKINTER_AVAILABLE = False
    print("警告: tkinter不可用，文件选择功能将不可用")



def get_base_path():
    """获取程序所在目录"""
    if getattr(sys, 'frozen', False):
        # 打包成exe后的路径
        base_path = os.path.dirname(sys.executable)
    else:
        # 脚本运行时的路径
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path

def get_loader_exe_path():
    """获取Mods_Loader/loader.exe的完整路径"""
    base_path = get_base_path()
    loader_dir = os.path.join(base_path, "Mods_Loader")
    loader_path = os.path.join(loader_dir, "loader.exe")
    
    # 检查loader.exe是否存在
    if os.path.exists(loader_path):
        return loader_path
    else:
        # 检查Mods_Loader文件夹是否存在
        if not os.path.exists(loader_dir):
            return None
        
        # 尝试在Mods_Loader目录下寻找loader.exe
        for file in os.listdir(loader_dir):
            if file.lower() == "loader.exe":
                return os.path.join(loader_dir, file)
        return None

def get_inject_exe_path():
    """获取Inject.exe的完整路径"""
    base_path = get_base_path()
    inject_path = os.path.join(base_path, "Inject.exe")
    
    # 检查Inject.exe是否存在
    if os.path.exists(inject_path):
        return inject_path
    else:
        # 尝试在当前目录下寻找Inject.exe
        for file in os.listdir(base_path):
            if file.lower() == "inject.exe":
                return os.path.join(base_path, file)
        return None

def is_endfield_running():
    """检查Endfield.exe进程是否正在运行"""
    try:
        # 使用tasklist命令检查进程
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq Endfield.exe'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # 如果输出中包含Endfield.exe，说明进程正在运行
        return "Endfield.exe" in result.stdout
    except Exception as e:
        print(f"[警告] 检查进程时出错: {e}")
        return False

def kill_endfield_process():
    """强制结束Endfield.exe进程"""
    try:
        result = subprocess.run(
            ['taskkill', '/F', '/IM', 'Endfield.exe'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode == 0:
            print("[完成] 已强制结束Endfield.exe进程")
            return True
        else:
            print(f"[警告] 结束进程失败: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[错误] 结束进程时出错: {e}")
        return False

def ask_kill_endfield():
    """询问用户是否强制结束已运行的Endfield.exe进程"""
    if not TKINTER_AVAILABLE:
        print("[警告] 检测到Endfield.exe进程正在运行，但tkinter不可用，无法弹窗确认")
        print("[提示] 请手动结束游戏进程后再运行此程序")
        return False, False  # 返回两个值：是否继续，是否成功结束进程
    
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        
        result = messagebox.askyesno(
            "检测到游戏正在运行",
            "检测到 明日方舟：终末地Endfield.exe进程正在运行。\n\n"
            "接下来将强行终止Endfield.exe进程，以便reshade注入流程可以正常进行。\n\n"
            "是否强制结束已运行的Endfield.exe进程？",
            icon=messagebox.WARNING
        )
        root.destroy()
        
        if result:
            # 用户选择结束进程
            if kill_endfield_process():
                return True, True  # 继续启动，进程已结束
            else:
                # 进程结束失败，询问是否继续
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                
                continue_result = messagebox.askyesno(
                    "进程结束失败",
                    "无法结束Endfield.exe进程。\n\n"
                    "是否仍然继续启动？\n"
                    "这可能会导致注入失败。",
                    icon=messagebox.WARNING
                )
                root.destroy()
                
                if continue_result:
                    return True, False  # 继续启动，进程未结束
                else:
                    return False, False  # 不继续启动
        else:
            # 用户选择不结束进程，询问是否继续启动
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            
            continue_result = messagebox.askyesno(
                "确认继续启动",
                "您选择不结束已运行的进程。\n\n"
                "继续启动会导致注入失败或游戏异常。\n\n"
                "是否仍然继续启动？",
                icon=messagebox.WARNING
            )
            root.destroy()
            
            if continue_result:
                return True, False  # 继续启动，进程未结束
            else:
                return False, False  # 不继续启动
                
    except Exception as e:
        print(f"[错误] 弹窗确认时出错: {e}")
        return False, False

def run_loader():
    """运行Mods_Loader/loader.exe（如果存在）- 屏蔽控制台输出"""
    loader_path = get_loader_exe_path()
    
    if not loader_path or not os.path.exists(loader_path):
        print(f"[信息] 未找到Mods_Loader/loader.exe，跳过此流程")
        return True  # 返回True表示跳过是正常的
    
    
    try:
        # 获取loader.exe所在目录
        loader_dir = os.path.dirname(loader_path)
        
        # 在loader目录中运行loader.exe，屏蔽所有输出
        result = subprocess.run(
            [loader_path],
            cwd=loader_dir,  # 设置工作目录为Mods_Loader文件夹
            shell=True,
            stdout=subprocess.DEVNULL,  # 屏蔽标准输出
            stderr=subprocess.DEVNULL,  # 屏蔽错误输出
            creationflags=subprocess.CREATE_NO_WINDOW  # 不显示控制台窗口
        )
        
        if result.returncode == 0:
            return False
        else:
            print(f"[警告] loader.exe返回码: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"[错误] 执行loader.exe时出错: {e}")
        return False

def run_inject():
    """运行Inject.exe Endfield.exe命令 - 屏蔽控制台输出"""
    inject_path = get_inject_exe_path()
    
    if not inject_path or not os.path.exists(inject_path):
        print(f"[错误] 未找到Inject.exe文件")
        print(f"[提示] 请将Inject.exe放在程序目录: {get_base_path()}")
        return False
    
    
    try:
        # 获取程序所在目录
        base_path = get_base_path()
        
        # 在程序目录中运行Inject.exe，屏蔽所有输出
        result = subprocess.run(
            [inject_path, "Endfield.exe"],
            cwd=base_path,  # 设置工作目录
            shell=True,
            stdout=subprocess.DEVNULL,  # 屏蔽标准输出
            stderr=subprocess.DEVNULL,  # 屏蔽错误输出
            creationflags=subprocess.CREATE_NO_WINDOW  # 不显示控制台窗口
        )
        
        if result.returncode == 0:
            return False
        else:
            print(f"[警告] Inject.exe返回码: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"[错误] 执行Inject.exe时出错: {e}")
        return False


def get_game_path_file():
    """获取游戏路径文件的完整路径"""
    base_path = get_base_path()
    return os.path.join(base_path, "game load.txt")

def save_game_path(game_dir):
    """保存游戏路径到game load.txt文件"""
    try:
        file_path = get_game_path_file()
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(game_dir)
        print(f"[保存] 游戏路径已保存")
        return True
    except Exception as e:
        print(f"[错误] 保存游戏路径时出错: {e}")
        return False

def load_game_path():
    """从game load.txt文件加载游戏路径"""
    try:
        file_path = get_game_path_file()
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                game_dir = f.read().strip()
            if game_dir and os.path.exists(game_dir):
                return game_dir
    except Exception as e:
        print(f"[错误] 读取game load.txt时出错: {e}")
    return None

def select_exe_file_with_gui():
    """使用Windows文件资源管理器选择Endfield.exe文件（在主线程中调用）"""
    if not TKINTER_AVAILABLE:
        print("[错误] tkinter不可用，无法使用文件选择器")
        return None, None
    
    try:
        # 创建Tkinter根窗口但不显示
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        root.attributes("-topmost", True)  # 置顶
        
        # 设置文件选择器选项
        file_path = filedialog.askopenfilename(
            title="请选择 明日方舟：终末地 启动程序 (Endfield.exe)",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")],
            initialdir=os.path.expanduser("~")
        )
        
        root.destroy()  # 销毁窗口
        
        if file_path:
            # 返回文件路径及其所在目录
            return file_path, os.path.dirname(file_path)
        else:
            return None, None
            
    except Exception as e:
        print(f"[错误] 使用文件资源管理器时出错: {e}")
        return None, None

def is_valid_endfield_exe(file_path):
    """检查文件是否是有效的Endfield.exe"""
    if not file_path or not os.path.exists(file_path):
        return False
    
    # 检查文件名
    file_name = os.path.basename(file_path).lower()
    
    # 允许文件名中包含"endfield"（不区分大小写）
    if "endfield" in file_name and file_name.endswith(".exe"):
        return True
    
    return False

def get_endfield_exe_path():
    """让用户选择Endfield.exe，直到选择正确或用户取消"""
    if not TKINTER_AVAILABLE:
        print("[错误] tkinter不可用，无法使用文件选择器")
        return None, None
    
    print("[提示] 请选择 明日方舟：终末地 的启动程序 (Endfield.exe)...")
    
    while True:
        exe_path, exe_dir = select_exe_file_with_gui()
        
        # 用户关闭了选择窗口
        if not exe_path or not exe_dir:
            print("[取消] 用户取消了文件选择")
            return None, None
        
        # 检查是否是Endfield.exe
        if is_valid_endfield_exe(exe_path):
            print(f"[选择] 已选择: {os.path.basename(exe_path)}")
            return exe_path, exe_dir
        else:
            # 显示错误提示
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            
            file_name = os.path.basename(exe_path)
            messagebox.showwarning(
                "文件选择错误",
                f"当前选择的文件 \"{file_name}\"，不是 明日方舟：终末地 的启动程序 Endfield.exe。\n"
                f"请重新选择正确的Endfield.exe文件。"
            )
            root.destroy()
            
            print(f"[错误] 当前选择的文件 \"{file_name}\"，不是 明日方舟：终末地 的启动程序 Endfield.exe，请重新选择")

def check_reshade_files(game_dir):
    """检查游戏目录中ReShade文件是否包含正确的识别码"""
    
    # 删除ReShade2.ini和ReShade3.ini（如果存在）
    files_to_delete = ["ReShade2.ini", "ReShade3.ini"]
    for file_name in files_to_delete:
        file_path = os.path.join(game_dir, file_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[删除] 已删除文件: {file_name}")
            except Exception as e:
                print(f"[错误] 删除文件 {file_name} 时出错: {e}")
    
    # 检查ReShade.ini文件是否存在
    reshade_ini_path = os.path.join(game_dir, "ReShade.ini")
    
    if not os.path.exists(reshade_ini_path):
        return False, False
    
    # 如果文件存在，检查识别码
    try:
        with open(reshade_ini_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查[GENERAL]块中的EffectSearchPaths
        general_section_match = re.search(r'\[GENERAL\](.*?)(?=\n\[|\Z)', content, re.DOTALL)
        if general_section_match:
            general_content = general_section_match.group(1)
            effect_search_paths_match = re.search(r'EffectSearchPaths=(.*)', general_content)
            
            if effect_search_paths_match:
                paths_value = effect_search_paths_match.group(1)
                # 提取第一条路径（逗号分隔的第一个部分）
                first_path = paths_value.split(',')[0].strip()
                
                # 检查是否是识别码
                target_identifier = "by_RUA-RUA *ID code. Don't delete*"
                if first_path == target_identifier:
                    return True, True
                else:
                    return True, False
            else:
                print(f"[检测] EffectSearchPaths参数未找到")
                return True, False
        else:
            print(f"[检测] [GENERAL]块未找到")
            return True, False
            
    except Exception as e:
        print(f"[错误] 读取ReShade.ini时出错: {e}")
        return True, False

def copy_and_update_reshade_ini(game_dir):
    """复制并更新ReShade.ini文件，先备份原有文件"""
    # 获取程序所在目录
    base_path = get_base_path()
    source_ini_path = os.path.join(base_path, "ReShade", "ReShade.ini")
    
    # 检查源文件是否存在
    if not os.path.exists(source_ini_path):
        print(f"[错误] 未找到ReShade.ini文件")
        print(f"[提示] 请将ReShade.ini放在程序目录的ReShade文件夹中: {os.path.join(base_path, 'ReShade')}")
        return False
    
    # 构建目标路径
    target_ini_path = os.path.join(game_dir, "ReShade.ini")
    backup_ini_path = os.path.join(game_dir, "ReShade配置备份.ini")
    
    try:
        # 检查目标目录是否已存在ReShade.ini文件
        if os.path.exists(target_ini_path):
            print(f"[检测] 发现已存在的ReShade.ini文件，进行备份...")
            
            # 备份原有文件
            shutil.copy2(target_ini_path, backup_ini_path)
            print(f"[备份] 原有配置文件已备份为: {backup_ini_path}")
        
        # 读取源文件内容
        with open(source_ini_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 构建基础路径（脚本所在目录的ReShade文件夹路径）
        base_reshade_path = os.path.join(base_path, "ReShade")
        
        # 定义要修改的参数和对应的新值
        updates = {
            'AddonPath': os.path.join(base_reshade_path, "Addons"),
            'EffectSearchPaths': f"by_RUA-RUA *ID code. Don't delete*,{os.path.join(base_reshade_path, 'reshade-shaders', 'Shaders', '**')}",
            'PresetPath': os.path.join(base_reshade_path, "Presets", "聚焦.ini"),
            'TextureSearchPaths': os.path.join(base_reshade_path, "reshade-shaders", "Textures", "**"),
            'SoundPath': os.path.join(base_reshade_path, "sound", "camara.wav"),
            'EditorFont': os.path.join(base_reshade_path, "Fonts", "MiSans-Bold.ttf"),
            'Font': os.path.join(base_reshade_path, "Fonts", "MiSans-Bold.ttf"),
            'LatinFont': os.path.join(base_reshade_path, "Fonts", "MiSans-Bold.ttf")
        }
        
        # 按行处理内容
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # 检查是否是我们要修改的参数
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                
                # 检查是否是我们要修改的参数
                if key in updates:
                    new_line = f"{key}={updates[key]}"
                    new_lines.append(new_line)
                    print(f"[更新] 修改参数: {key} = {updates[key]}")
                    continue
            
            # 如果不是要修改的行，保持原样
            new_lines.append(line)
        
        # 将修改后的内容写回文件
        new_content = '\n'.join(new_lines)
        
        # 写入目标文件
        with open(target_ini_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"[完成] ReShade.ini文件已复制并更新到: {target_ini_path}")
        return True
        
    except Exception as e:
        print(f"[错误] 复制和更新ReShade.ini时出错: {e}")
        return False

def check_and_update_reshade_files(game_dir):
    """检查并更新ReShade文件（替换原来的解压功能）"""
    # 获取程序所在目录
    base_path = get_base_path()
    
    # 检查是否需要更新
    ini_exists, valid_identifier = check_reshade_files(game_dir)
    
    if not ini_exists or not valid_identifier:
        missing_reason = "ReShade.ini文件不存在" if not ini_exists else "识别码不匹配"
        print(f"[检测] 需要更新ReShade文件: {missing_reason}")
        
        # 询问用户是否更新
        if TKINTER_AVAILABLE:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            
            result = messagebox.askyesno(
                "需要更新ReShade文件",
                f"检测到游戏目录的ReShade文件需要更新:\n{missing_reason}\n\n"
                f"现在将复制并更新ReShade.ini文件到游戏目录，是否继续？\n\n"
                f"游戏目录: {game_dir}"
            )
            root.destroy()
            
            if result:
                return copy_and_update_reshade_ini(game_dir)
            else:
                print(f"[跳过] 用户取消了更新操作")
                return None  # 返回None表示用户取消
        else:
            # 如果没有tkinter，自动尝试更新
            print(f"[自动] 尝试自动更新ReShade.ini文件...")
            return copy_and_update_reshade_ini(game_dir)
    else:
        print(f"[检测] ReShade配置文件识别码验证通过，跳过更新")
        return True

def run_endfield_from_directory(game_dir):
    """从指定目录运行Endfield.exe"""
    
    try:
        # 检查目录是否存在
        if not os.path.exists(game_dir):
            print(f"[错误] 目录不存在: {game_dir}")
            return False
            
        # 保存当前目录
        original_dir = os.getcwd()
        
        # 切换到游戏目录
        os.chdir(game_dir)
        
        # 检查Endfield.exe是否存在
        if not os.path.exists("Endfield.exe"):
            print(f"[错误] 目录中未找到Endfield.exe")
            os.chdir(original_dir)  # 切换回原目录
            return False
        
        # 游戏启动前再次删除ReShade2.ini和ReShade3.ini
        files_to_delete = ["ReShade2.ini", "ReShade3.ini"]
        for file_name in files_to_delete:
            file_path = os.path.join(game_dir, file_name)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"[删除] 游戏启动前删除: {file_name}")
                except Exception as e:
                    print(f"[错误] 删除文件 {file_name} 时出错: {e}")
        
        # 检查ReShade配置文件识别码
        ini_exists, valid_identifier = check_reshade_files(game_dir)
        
        # 如果ini文件不存在，或者存在但识别码不匹配，则需要更新
        if not ini_exists or not valid_identifier:
            # 调用新的更新函数（替换原来的解压功能）
            update_result = check_and_update_reshade_files(game_dir)
            
            if update_result is None:  # 用户取消
                os.chdir(original_dir)
                return None
            elif not update_result:
                print(f"[错误] 更新ReShade文件失败")
                os.chdir(original_dir)
                return False
        else:
            print(f"[检测] ReShade配置文件识别码验证通过，跳过更新")
        
        
        print(f"[执行] 运行: Endfield.exe -force-d3d11")
        
        # 使用Popen启动进程，使用CREATE_NEW_PROCESS_GROUP使其独立
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, 'DETACHED_PROCESS'):
            creation_flags |= subprocess.DETACHED_PROCESS
        
        process = subprocess.Popen(
            ["Endfield.exe", "-force-d3d11"],
            shell=True,
            stdout=subprocess.DEVNULL,  # 屏蔽游戏输出
            stderr=subprocess.DEVNULL,  # 屏蔽游戏错误
            creationflags=creation_flags  # 关键：使进程独立
        )
        
        # 短暂等待检查进程是否启动成功
        time.sleep(2)
        
        # 检查进程是否仍在运行
        if process.poll() is not None:
            # 进程已结束
            print(f"[错误] 游戏启动失败")
            os.chdir(original_dir)
            return False
        else:
            # 立即关闭进程句柄，使游戏完全独立
            process.terminate()
            process.wait(timeout=1)
            os.chdir(original_dir)
            return True
            
    except FileNotFoundError:
        print("[错误] 找不到Endfield.exe文件")
        return False
    except Exception as e:
        print(f"[错误] 启动游戏时出错: {e}")
        # 确保切换回原目录
        try:
            os.chdir(original_dir)
        except:
            pass
        return False

def run_endfield_from_directory(game_dir):
    """从指定目录运行Endfield.exe"""
    
    try:
        # 检查目录是否存在
        if not os.path.exists(game_dir):
            print(f"[错误] 目录不存在: {game_dir}")
            return False
            
        # 保存当前目录
        original_dir = os.getcwd()
        
        # 切换到游戏目录
        os.chdir(game_dir)
        
        # 检查Endfield.exe是否存在
        if not os.path.exists("Endfield.exe"):
            print(f"[错误] 目录中未找到Endfield.exe")
            os.chdir(original_dir)  # 切换回原目录
            return False
        
        # 检查ReShade配置文件识别码
        ini_exists, valid_identifier = check_reshade_files(game_dir)
        
        # 如果ini文件不存在，或者存在但识别码不匹配，则需要更新
        if not ini_exists or not valid_identifier:
            # 调用新的更新函数（替换原来的解压功能）
            update_result = check_and_update_reshade_files(game_dir)
            
            if update_result is None:  # 用户取消
                os.chdir(original_dir)
                return None
            elif not update_result:
                print(f"[错误] 更新ReShade文件失败")
                os.chdir(original_dir)
                return False
        else:
            print(f"[检测] ReShade配置文件识别码验证通过，跳过更新")
        
        
        print(f"[执行] 运行: Endfield.exe -force-d3d11")
        
        # 使用Popen启动进程，使用CREATE_NEW_PROCESS_GROUP使其独立
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, 'DETACHED_PROCESS'):
            creation_flags |= subprocess.DETACHED_PROCESS
        
        process = subprocess.Popen(
            ["Endfield.exe", "-force-d3d11"],
            shell=True,
            stdout=subprocess.DEVNULL,  # 屏蔽游戏输出
            stderr=subprocess.DEVNULL,  # 屏蔽游戏错误
            creationflags=creation_flags  # 关键：使进程独立
        )
        
        # 短暂等待检查进程是否启动成功
        time.sleep(2)
        
        # 检查进程是否仍在运行
        if process.poll() is not None:
            # 进程已结束
            print(f"[错误] 游戏启动失败")
            os.chdir(original_dir)
            return False
        else:
            print(f"[成功] 游戏已启动 (PID: {process.pid})")
            # 立即关闭进程句柄，使游戏完全独立
            process.terminate()
            process.wait(timeout=1)
            os.chdir(original_dir)
            return True
            
    except FileNotFoundError:
        print("[错误] 找不到Endfield.exe文件")
        return False
    except Exception as e:
        print(f"[错误] 启动游戏时出错: {e}")
        # 确保切换回原目录
        try:
            os.chdir(original_dir)
        except:
            pass
        return False

def cleanup_ngx_updater():
    """清理多余的 NGX updater 进程"""
    try:
        result = subprocess.run(
            ['taskkill', '/F', '/IM', 'nvngx_update.exe'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            print("[清理] 已结束多余的 NGX updater 进程")
        # 注意：这里不检查返回值，因为如果进程不存在也会返回错误
    except Exception as e:
        print(f"[信息] 清理 NGX updater 时出错: {e}")

def run_endfield_game():
    """运行Endfield游戏"""
    time.sleep(3)  # 短暂延迟，让Inject先启动
    
    
    # 从文件加载游戏路径
    game_dir = load_game_path()
    
    # 如果文件中有有效路径，尝试运行
    if game_dir:
        print(f"[读取] 使用已保存的游戏路径: {game_dir}")
        result = run_endfield_from_directory(game_dir)
        if result is None:  # 用户取消解压
            return None
        elif result:
            return True
        else:
            print("[提示] 保存的路径无效，需要重新选择")
    
    # 如果文件没有有效路径或启动失败，让用户选择
    exe_path, exe_dir = get_endfield_exe_path()
    
    if not exe_path or not exe_dir:
        print("[取消] 游戏启动已取消")
        return False
    
    # 保存路径到文件
    if save_game_path(exe_dir):
        # 尝试从新目录运行
        result = run_endfield_from_directory(exe_dir)
        if result is None:  # 用户取消解压
            return None
        elif result:
            return True
        else:
            # 如果启动失败，删除保存的路径文件
            print("[清理] 删除错误的路径记录")
            try:
                file_path = get_game_path_file()
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"[错误] 删除路径文件时出错: {e}")
            return False
    else:
        print("[错误] 保存路径失败")
        return False

def wait_for_exit(timeout=3):
    """等待用户按键或超时后退出"""
    # 如果是打包的exe，使用不同的退出方式
    if getattr(sys, 'frozen', False):
        print(f"\n请稍候...")
        time.sleep(2)
    else:
        time.sleep(2)

def set_window_title(title="终末地-reshade"):
    """设置进程窗口标题"""
    try:
        # 设置控制台窗口标题（如果有控制台窗口）
        if hasattr(ctypes, 'windll'):
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        
        # 设置进程名称（影响任务栏显示）
        if hasattr(sys, 'set_application_name'):
            sys.set_application_name(title)
            
        # 设置窗口标题
        if hasattr(ctypes, 'windll'):
            try:
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.SetWindowTextW(hwnd, title)
            except:
                pass
                
    except Exception as e:
        print(f"[信息] 设置窗口标题时出错: {e}")

def setup_main_window():
    """设置主窗口属性（如果存在GUI）"""
    if not TKINTER_AVAILABLE:
        return None
    
    try:
        # 创建隐藏的主窗口并设置标题
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        root.title("终末地-reshade")
        
        # 设置任务栏显示名称
        if hasattr(ctypes, 'windll'):
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                ctypes.windll.user32.SetWindowTextW(hwnd, "终末地-reshade")
            except:
                pass
        
        return root
    except Exception as e:
        print(f"[信息] 设置主窗口时出错: {e}")
        return None
    
def main():
    """主函数：以管理员权限运行，并顺序启动三个功能"""
    
    # 设置窗口标题
    set_window_title("终末地-reshade")
    
    # 设置主窗口（如果有GUI）
    main_window = setup_main_window()


    print("=" * 50)
    print("明日方舟：终末地 游戏启动器 (ReShade注入 + Mods加载)")
    print("=" * 50)
    
    # 获取程序目录
    base_path = get_base_path()
    print(f"[位置] 程序目录: {base_path}")
    
    # 检查Endfield.exe进程是否正在运行
    if is_endfield_running():
        print("[检测] 发现Endfield.exe进程正在运行")
        continue_start, process_ended = ask_kill_endfield()
        
        if not continue_start:
            # 用户取消启动
            print("[取消] 用户取消启动，程序退出")
            print("\n[完成] 启动流程已取消")
            wait_for_exit(3)
            return
        
        # 等待进程完全结束
        if process_ended:
            print("等待Endfield.exe进程彻底终止（2秒）")
            time.sleep(2)
            # 再次检查确认进程已结束
            if is_endfield_running():
                print("[警告] 进程可能未完全结束，继续启动可能会有风险")
    
    # 检查Mods_Loader/loader.exe是否存在
    loader_path = get_loader_exe_path()
    if not loader_path:
        print(f"[信息] 未找到Mods_Loader/loader.exe，跳过此流程")
        loader_found = False
    else:
        loader_found = True
    
    # 检查Inject.exe是否存在
    inject_path = get_inject_exe_path()
    if not inject_path:
        print(f"[警告] 未找到Inject.exe，跳过注入步骤")
        inject_found = False
    else:
        inject_found = True
    
    # 检查tkinter是否可用
    if not TKINTER_AVAILABLE:
        print("[警告] tkinter不可用，文件选择功能将不可用")
    
    # 检查游戏路径是否存在
    game_path = load_game_path()
    if not game_path:
        print("[提示] 未找到游戏路径，首次运行需要选择")
    
    # 顺序启动三个功能
    success = True
    
    # 1. 先启动Mods_Loader/loader.exe（如果存在）
    if loader_found:
        loader_thread = threading.Thread(target=run_loader, name="LoaderThread", daemon=True)
        loader_thread.start()
        print("[完成] loader.exe已启动")
    else:
        print("[信息] 跳过Mods_Loader/loader.exe启动")
    
    # 2. 然后启动Inject.exe
    if inject_found:
        inject_thread = threading.Thread(target=run_inject, name="InjectThread", daemon=True)
        inject_thread.start()
        print("[完成] Inject.exe已启动")
    else:
        print("[警告] 跳过Inject.exe注入")
    
    # 3. 最后启动游戏
    print("准备启动明日方舟：终末地...")
    cleanup_ngx_updater()
    time.sleep(2)
    game_result = run_endfield_game()
    
    # 显示最终结果
    print("\n" + "=" * 50)
    
    if game_result is None:  # 用户取消解压
        print("[结果] 用户取消，启动流程终止")
    elif game_result:
        print("[完成] 所有组件已按顺序启动")
    else:
        print("[结果] 游戏启动失败")
    
    wait_for_exit(5)
    return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[信息] 检测到中断信号，程序退出")
    except Exception as e:
        print(f"\n[错误] 程序执行出错: {e}")
        wait_for_exit(5)