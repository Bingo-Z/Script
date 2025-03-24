import os  # 提供操作系统相关功能
import filecmp  # 用于文件比较
import json  # 处理JSON格式数据
from pathlib import Path  # 提供路径操作功能
from datetime import datetime  # 获取当前时间
import difflib  # 用于比较文本差异

def clean_empty_dicts(d):
    """递归清理字典中的空字典和空列表"""
    if isinstance(d, dict):  # 如果输入是字典
        result = {}  # 创建空字典存储结果
        for k, v in d.items():  # 遍历字典的键值对
            cleaned = clean_empty_dicts(v)  # 递归清理值
            if cleaned:  # 只保留非空的值
                result[k] = cleaned
        return result
    elif isinstance(d, list):  # 如果输入是列表
        return d if d else None  # 如果列表为空返回 None
    return d  # 返回原始值

def compare_file_contents(file1, file2):
    """比较两个文件的内容是否相同"""
    try:
        return filecmp.cmp(file1, file2, shallow=False)  # 深度比较文件内容
    except:
        return False  # 如果比较失败返回False

def compare_folders(dir1, dir2, output_file):
    # 初始化结果字典
    result = {
        "comparison_info": {
            "base_folder": dir1,  # 基准文件夹路径
            "compare_folder": dir2,  # 比较文件夹路径
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 当前时间
        },
        "differences": {
            "changes": dict(),  # 存储文件夹结构变化
            "total_changes": 0,  # 总变化数量
            "different_files": []  # 存储内容不同的文件列表
        }
    }
    
    # 获取两个文件夹的结构
    dir1_structure = {}
    dir2_structure = {}
    
    # 获取第一个文件夹（基准）的结构
    for root, dirs, _ in os.walk(dir1):  # 遍历文件夹
        rel_path = os.path.relpath(root, dir1)  # 获取相对路径
        dir1_structure[rel_path] = set(dirs)  # 存储目录结构
    
    # 获取第二个文件夹的结构
    for root, dirs, _ in os.walk(dir2):
        rel_path = os.path.relpath(root, dir2)
        dir2_structure[rel_path] = set(dirs)
            
    # 比较文件夹结构
    changes_dict = {}
    processed_paths = set()
    
    all_paths = set(dir1_structure.keys()) | set(dir2_structure.keys())  # 获取所有路径的并集
    
    # 找出第一个有变化的目录作为基准点
    base_path = None
    for rel_path in sorted(all_paths):  # 按顺序遍历所有路径
        dir1_dirs = dir1_structure.get(rel_path, set())
        dir2_dirs = dir2_structure.get(rel_path, set())
        if dir1_dirs != dir2_dirs:  # 如果发现差异
            base_path = rel_path
            break
    
    # 处理变化
    for rel_path in sorted(all_paths):
        # 如果找到了基准路径，只处理基准路径及其直接子目录
        if base_path:
            if not rel_path.startswith(base_path):
                continue
            # 跳过比基准路径深两层以上的目录
            #注意：通过空值+1还是-1还是+2来控制遍历长度
            if rel_path.count('\\') > base_path.count('\\') + 1:
                continue
        
        dir1_dirs = dir1_structure.get(rel_path, set())
        dir2_dirs = dir2_structure.get(rel_path, set())
        
        new_dirs = dir2_dirs - dir1_dirs  # 计算新增目录
        deleted_dirs = dir1_dirs - dir2_dirs  # 计算删除目录
        
        if new_dirs or deleted_dirs:  # 如果有变化
            processed_paths.add(rel_path)
            
            if rel_path == '.':  # 处理根目录
                parent_path = ''
            else:
                parent_path = rel_path
            
            changes_dict[parent_path] = {
                "new": {},
                "deleted": {}
            }
            
            # 获取新增文件夹的直接子文件夹
            for new_dir in new_dirs:
                new_dir_path = os.path.join(dir2, parent_path, new_dir)
                sub_dirs = []
                if os.path.exists(new_dir_path):
                    sub_dirs = [d for d in os.listdir(new_dir_path) 
                              if os.path.isdir(os.path.join(new_dir_path, d))]
                changes_dict[parent_path]["new"][new_dir] = sub_dirs
            
            # 获取删除文件夹的直接子文件夹
            for deleted_dir in deleted_dirs:
                deleted_dir_path = os.path.join(dir1, parent_path, deleted_dir)
                sub_dirs = []
                if os.path.exists(deleted_dir_path):
                    sub_dirs = [d for d in os.listdir(deleted_dir_path) 
                              if os.path.isdir(os.path.join(deleted_dir_path, d))]
                changes_dict[parent_path]["deleted"][deleted_dir] = sub_dirs

    # 添加文件内容比较
    different_files = []
    for root, _, files in os.walk(dir1):  # 遍历基准文件夹
        rel_path = os.path.relpath(root, dir1)
        for file in files:
            file1_path = os.path.join(root, file)
            file2_path = os.path.join(dir2, rel_path, file)
            
            # 检查文件2是否存在且内容不同
            if os.path.exists(file2_path) and not compare_file_contents(file1_path, file2_path):
                rel_file_path = os.path.join(rel_path, file).replace('\\', '/')
                if rel_file_path.startswith('./'):
                    rel_file_path = rel_file_path[2:]
                different_files.append(rel_file_path)
    
    # 更新结果
    if different_files:
        result["differences"]["different_files"] = sorted(different_files)
    else:
        result["differences"]["different_files"] = "没有"

    if changes_dict:
        cleaned_changes = clean_empty_dicts(changes_dict)
        if cleaned_changes:
            result["differences"]["changes"] = cleaned_changes
            result["differences"]["total_changes"] = sum(
                len(data.get("new", {})) + len(data.get("deleted", {})) 
                for data in cleaned_changes.values()
            )

    # 写入JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 从命令行获取文件夹路径
    folder1 = input("请输入第一个文件夹的完整路径: ").strip()
    folder2 = input("请输入第二个文件夹的完整路径: ").strip()
    
    # 转换为绝对路径
    folder1 = os.path.abspath(folder1)
    folder2 = os.path.abspath(folder2)
    
    # 设置输出文件路径为D盘根目录
    output_file = "D:\\differences.json"
    
    # 执行比较
    compare_folders(folder1, folder2, output_file)
    print(f"比较结果已写入 {output_file}")
