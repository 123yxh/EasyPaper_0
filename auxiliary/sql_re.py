import mysql.connector
from mysql.connector import Error

# 检查数据库是否正常开始
try:
    # 连接数据库
    connection = mysql.connector.connect(
        host='localhost',
        port=3306,
        database='easypaper',
        user='yxh',
        password=''
    )

    if connection.is_connected():
        print("✅ 成功连接到 MySQL 数据库")

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users")
        
        # 获取字段名（列名）
        columns = [desc[0] for desc in cursor.description]
        records = cursor.fetchall()

        print(f"📊 查询结果（共 {len(records)} 条）:")
        print(" | ".join(columns))  # 打印表头

        for row in records:
            print(" | ".join(str(cell) for cell in row))  # 打印每行数据

except Error as e:
    print("❌ 数据库连接或查询失败：", e)

finally:
    if 'connection' in locals() and connection.is_connected():
        cursor.close()
        connection.close()
        print("🔌 数据库连接已关闭")
