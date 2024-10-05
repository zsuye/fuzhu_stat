import pandas as pd

# 读取GBK编码的CSV文件
df = pd.read_csv("D:\\桂香园\\ExportOrderList202403252230.csv", encoding='GBK')

# 在订单号前加上单引号
df['订单编号'] = "'" + df['订单编号'].astype(str)

# 将DataFrame保存为Excel文件
df.to_excel("D:\\桂香园\\ExportOrderList202403252230.xlsx", index=False)
