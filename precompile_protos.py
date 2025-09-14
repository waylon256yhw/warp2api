#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Protobuf预编译脚本

此脚本用于预编译.proto文件，生成描述符集文件，避免运行时依赖grpcio-tools。
运行此脚本后，服务器将使用预编译的描述符集，而不是运行时编译.proto文件。
"""
import os
import sys
import pathlib
import argparse
from typing import List

# 确保grpcio-tools已安装（仅在预编译时需要）
try:
    from grpc_tools import protoc
except ImportError:
    print("错误: grpcio-tools未安装。请运行: pip install grpcio-tools")
    sys.exit(1)

# 尝试获取grpc_tools的_proto目录
try:
    from importlib.resources import files as pkg_files
    tool_inc = str(pkg_files("grpc_tools").joinpath("_proto"))
except Exception:
    tool_inc = None
    print("警告: 无法获取grpc_tools的_proto目录，可能影响编译结果")

# 默认proto目录
DEFAULT_PROTO_DIR = pathlib.Path(__file__).parent / "proto"
# 默认输出文件
DEFAULT_OUTPUT = pathlib.Path(__file__).parent / "proto" / "compiled_descriptors.pb"


def find_proto_files(root: pathlib.Path) -> List[str]:
    """查找必要的.proto文件"""
    if not root.exists():
        print(f"错误: proto目录不存在: {root}")
        return []
    
    essential_files = [
        "request.proto",
        "response.proto", 
        "task.proto",
        "attachment.proto",
        "file_content.proto",
        "input_context.proto",
        "citations.proto"
    ]
    
    found_files = []
    for file_name in essential_files:
        file_path = root / file_name
        if file_path.exists():
            found_files.append(str(file_path))
            print(f"找到核心proto文件: {file_name}")
    
    if not found_files:
        print("警告: 未找到核心proto文件，扫描所有文件...")
        exclude_patterns = [
            "unittest", "test", "sample_messages", "java_features", 
            "legacy_features", "descriptor_test"
        ]
        
        for proto_file in root.rglob("*.proto"):
            file_name = proto_file.name.lower()
            if not any(pattern in file_name for pattern in exclude_patterns):
                found_files.append(str(proto_file))
    
    print(f"选择了 {len(found_files)} 个proto文件进行编译")
    return found_files


def build_descriptor_set(proto_files: List[str], includes: List[str], output_file: pathlib.Path) -> bool:
    """编译proto文件，生成描述符集"""
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 构建protoc命令行参数
    args = ["protoc", f"--descriptor_set_out={output_file}", "--include_imports"]
    
    # 添加包含目录
    for inc in includes:
        args.append(f"-I{inc}")
    
    # 添加grpc_tools的_proto目录（如果可用）
    if tool_inc:
        args.append(f"-I{tool_inc}")
    
    # 添加proto文件
    args.extend(proto_files)
    
    # 运行protoc
    print(f"运行protoc编译命令: {' '.join(args)}")
    rc = protoc.main(args)
    
    if rc != 0 or not output_file.exists():
        print(f"错误: protoc编译失败，返回码: {rc}")
        return False
    
    print(f"✅ 成功生成描述符集文件: {output_file} ({output_file.stat().st_size} 字节)")
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Protobuf预编译工具")
    parser.add_argument("--proto-dir", type=str, default=str(DEFAULT_PROTO_DIR),
                        help=f"proto文件目录 (默认: {DEFAULT_PROTO_DIR})")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT),
                        help=f"输出描述符集文件 (默认: {DEFAULT_OUTPUT})")
    args = parser.parse_args()
    
    # 转换为Path对象
    proto_dir = pathlib.Path(args.proto_dir)
    output_file = pathlib.Path(args.output)
    
    # 查找proto文件
    proto_files = find_proto_files(proto_dir)
    if not proto_files:
        print("错误: 未找到任何proto文件")
        return 1
    
    # 编译proto文件
    success = build_descriptor_set(proto_files, [str(proto_dir)], output_file)
    if not success:
        return 1
    
    print("\n预编译完成！现在您可以修改warp2protobuf/core/protobuf.py，使其加载预编译的描述符集。")
    print("修改后，您可以从pyproject.toml中移除grpcio-tools依赖。")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
