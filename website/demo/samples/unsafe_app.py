"""
不安全代码示例 — 用于演示 Truffle 安全扫描
"""
import os
import subprocess
import pickle
import sqlite3

# 硬编码的 API Key（高危）
API_KEY = "sk-1234567890abcdef1234567890abcdef"

def unsafe_login():
    """SQL 注入漏洞"""
    username = input("请输入用户名: ")
    password = input("请输入密码: ")

    # 拼接 SQL 查询（高危！）
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    cursor.execute(query)
    return cursor.fetchone()


def execute_command():
    """运行系统命令"""
    cmd = input("请输入命令: ")
    os.system(cmd)  # 高危！


def process_data(data):
    """反序列化用户数据"""
    return pickle.loads(data)  # 高危！可执行任意代码


def delete_logs():
    """删除日志文件"""
    os.remove("/var/log/app.log")
    os.unlink("/tmp/old_data.tmp")


if __name__ == "__main__":
    # 暴力执行
    subprocess.run(["rm", "-rf", "/tmp/data"])  # 高危！
    print("API_KEY =", API_KEY)
