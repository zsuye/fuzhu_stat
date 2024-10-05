import pandas as pd
from typing import List, Tuple, Dict


def read_sheet(sheet_name: str) -> pd.DataFrame:
    """
    读取Excel工作表数据。
    参数:
    sheet_name (str): 工作表的名称。
    返回:
    pd.DataFrame: 工作表的数据。
    """
    # 这里需要将相应的文件路径和工作表名替换为实际的路径和名称
    return pd.read_excel("E:/桂香园/泰昌美电商管理11121716.xlsx", sheet_name=sheet_name)


def process_data(sales: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    """
    处理销售和库存数据。
    参数:
    sales (pd.DataFrame): 销售数据。
    inventory (pd.DataFrame): 入库与非销售出库数据。
    返回:
    pd.DataFrame: 处理后的合并数据。
    """
    # 销售数据的数量转为负数
    sales["数量"] *= -1

    # 合并数据
    combined_data = pd.concat([sales, inventory], ignore_index=True)

    # 按日期和产品名称分组，并计算每天每个产品的总数量变化
    daily_changes = combined_data.groupby(["日期", "产品名称"])["数量"].sum().reset_index()

    return daily_changes


def calculate_daily_inventory_snapshot(starting_snapshot: pd.DataFrame, daily_changes: pd.DataFrame) -> pd.DataFrame:
    """
    计算每天的库存快照。
    参数:
    starting_snapshot (pd.DataFrame): 起始库存快照。
    daily_changes (pd.DataFrame): 每天的库存变化数据。
    返回:
    pd.DataFrame: 每天的库存快照。
    """
    # 转换日期格式
    starting_snapshot['日期'] = pd.to_datetime(starting_snapshot['日期'])
    daily_changes['日期'] = pd.to_datetime(daily_changes['日期'])

    # 获取起始和结束日期
    start_date = starting_snapshot['日期'].min()
    end_date = daily_changes['日期'].max()

    # 初始化最终的库存快照
    final_snapshots = []

    # 当前库存状态
    current_inventory = starting_snapshot.set_index('产品名称').copy()

    # 遍历每天的变化，并更新库存快照
    for date in pd.date_range(start_date, end_date):
        # 如果当天有库存变化，更新当前库存状态
        if date in daily_changes['日期'].values:
            daily_update = daily_changes[daily_changes['日期'] == date]
            for _, change in daily_update.iterrows():
                product = change['产品名称']
                qty_change = change['数量']
                if product in current_inventory.index:
                    current_inventory.at[product, '数量'] += qty_change
                else:
                    # 使用 pd.concat 添加新行
                    new_row = pd.DataFrame({'日期': date, '数量': qty_change}, index=[product])
                    current_inventory = pd.concat([current_inventory, new_row])

        # 记录当天的库存快照
        snapshot = current_inventory.copy()
        snapshot['日期'] = date
        final_snapshots.append(snapshot.reset_index().rename(columns={'index': '产品名称'}))

    # 合并所有日快照
    final_snapshots_df = pd.concat(final_snapshots, ignore_index=True)

    return final_snapshots_df


def export_to_excel(df: pd.DataFrame, file_name: str):
    """
    将数据导出为Excel文件。
    参数:
    df (pd.DataFrame): 要导出的数据。
    file_name (str): 导出文件的名称。
    """
    df.to_excel(file_name, index=False)

# 读取数据
sales_data = read_sheet("销售")
inventory_data = read_sheet("入库与非销售出库")

# 处理数据
combined_data = process_data(sales_data, inventory_data)

# 提供的起始库存快照
starting_snapshot = pd.DataFrame(
    {
        "日期": [
            "2023/10/10",
            "2023/10/10",
            "2023/10/10",
            "2023/10/10",
            "2023/10/10",
            "2023/10/10",
        ],
        "产品名称": ["油炸腐竹350g", "切片竹2500g", "边角料500g", "边角料300g", "腐竹卷100g", "边角料400g"],
        "数量": [0, 2, 780, 0, 19, 87],
    }
)

# 计算库存快照
inventory_snapshot = calculate_daily_inventory_snapshot(starting_snapshot, combined_data)

# 导出结果到Excel文件
export_to_excel(inventory_snapshot, "inventory_snapshot.xlsx")

# 打印完成信息
print("库存快照已导出到 'inventory_snapshot.xlsx'")