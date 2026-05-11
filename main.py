# 导入命令行参数工具：让你可以在终端输入命令运行程序
import argparse
# 导入路径处理工具
from pathlib import Path

# 导入你刚才的核心工作流：解析会议纪要的主函数
from meeting_agent.workflow import run_meeting_extraction


# 主函数：程序入口点
def main():
    # 1. 创建命令行解析器，给工具起个名字和说明
    parser = argparse.ArgumentParser(description="AI 会议纪要结构化提取工具")
    
    # 2. 定义命令行参数
    parser.add_argument(
        "input",  # 参数名：input
        nargs="?",  # 可选，可传可不传
        default="data/input/test_meeting.docx",  # 默认文件路径
        help="输入的会议记录 docx 文件路径",
    )

    # 3. 获取你在终端输入的参数
    args = parser.parse_args()

    # 4. 把输入路径转成 Path 对象
    input_path = Path(args.input)

    # ======================
    # 核心：调用主程序！
    # 把 Word 丢进去，开始 AI 自动解析
    # ======================
    result = run_meeting_extraction(input_path)

    # 5. 把结果漂亮地打印到终端
    print("\n===== 会议纪要结构化结果 =====\n")
    print(result.model_dump_json(indent=2, ensure_ascii=False))

    # 6. 提示用户结果保存位置
    print("\n结果已保存到 data/output 文件夹。")


# 固定写法：只有直接运行这个文件时，才执行 main()
if __name__ == "__main__":
    main()