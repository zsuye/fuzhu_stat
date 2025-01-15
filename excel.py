from cgi import FieldStorage
from collections import defaultdict
from io import BytesIO
import os
import re
from tkinter import Tk, filedialog
from typing import List, Optional, Tuple, Union, Dict
import pandas as pd


def merge_excel_files_from_paths(file_paths: List[str]) -> pd.DataFrame:
    """
    Merge multiple Excel files from given file paths into a single DataFrame.

    Args:
    - file_paths (List[str]): List of file paths to the Excel files to be merged.

    Returns:
    - pd.DataFrame: Merged DataFrame.
    """
    dfs = []
    for file_path in file_paths:
        if file_path.endswith(".xlsx"):
            engine = "openpyxl"
        elif file_path.endswith(".xls"):
            engine = "xlrd"
        else:
            continue  # Skip unsupported file types
        df = pd.read_excel(file_path, engine=engine)
        dfs.append(df)
    # Check if the dfs list is empty
    if not dfs:
        return pd.DataFrame()
    combined_df = pd.concat(dfs, ignore_index=True)
    return combined_df


# Function to process "规格编码" column and adjust "数量"
def pdd_process_spec_and_quantity(row):
    # Replace TCM-2500G with QPZ-2500G
    row["规格编码"] = re.sub(
        r"TCM-2500G", "QPZ-2500G", str(row["规格编码"]), flags=re.IGNORECASE
    )

    spec_code = row["规格编码"]
    quantity = int(row["数量"])
    # Lanhua gan patterns
    # DG pattern
    match = re.search(r"^DG-?6\*(?:13|14)-(\d+)$", spec_code)
    if match:
        row["商品名称/简称"] = "6×13兰花干"
        row["数量"] = quantity * int(match.group(1))
        return row

    match = re.search(r"^DG6\*10-(\d+)$", spec_code)
    if match:
        row["商品名称/简称"] = "6×10兰花干"
        row["数量"] = quantity * int(match.group(1))
        return row

    # JHP pattern
    match = re.search(r"^JHP【6\*10】-(?:06\*(\d+)|(\d+))$", spec_code)
    if match:
        row["商品名称/简称"] = "6×10兰花干"
        number = match.group(1) or match.group(2)
        if match.group(1):  # If it's in 06*XX format
            row["数量"] = quantity * (int(number) * 6)
        else:  # If it's in direct number format
            row["数量"] = quantity * int(number)
        return row

    match = re.search(r"^JHP【6\*13】-(?:06\*(\d+)|(\d+))$", spec_code)
    if match:
        row["商品名称/简称"] = "6×13兰花干"
        number = match.group(1) or match.group(2)
        if match.group(1):  # If it's in 06*XX format
            row["数量"] = quantity * (int(number) * 6)
        else:  # If it's in direct number format
            row["数量"] = quantity * int(number)
        return row

    # Handle DG-CP-500g pattern
    if spec_code == "DG-CP-500g":
        row["商品名称/简称"] = "兰花干边角料500g"
        return row


    # \*(\d+)$
    match = re.search(r"\*(\d+).?$", spec_code, re.IGNORECASE)
    if match:
        row["数量"] = quantity * int(match.group(1))
        row["规格编码"] = spec_code.replace(match.group(0), "")
        return row

    # FZP-(\d+)
    match = re.search(r"FZP-(\d+)", spec_code, re.IGNORECASE)
    if match:
        row["数量"] = quantity * (int(match.group(1)) / 500)
        row["规格编码"] = "FZP-500g"
        return row

    # Z-QPZ-(\d+)
    match = re.search(r"Z-QPZ-(\d+)", spec_code, re.IGNORECASE)
    if match:
        row["数量"] = quantity * (int(match.group(1)) / 500)
        row["规格编码"] = "Z-QPZ-500G"
        return row

    # YZ-350G
    match = re.search(r"YZ-350G", spec_code, re.IGNORECASE)
    if match:
        row["数量"] = quantity
        row["规格编码"] = "YZ-350G"
        return row

    # YZ-(\d+)G
    match = re.search(r"YZ-(\d+)G", spec_code, re.IGNORECASE)
    if match:
        row["数量"] = quantity * (int(match.group(1)) / 500)
        row["规格编码"] = "YZ-500G"
        return row

    # S-BJ-(\d+)
    match = re.search(r"S-BJ-(\d+)", spec_code, re.IGNORECASE)
    if match:
        row["数量"] = quantity * (int(match.group(1)) / 500)
        row["规格编码"] = "S-BJ-500"
        return row

    # ll-YZ-(\d+)G
    match = re.search(r"ll-YZ-(\d+)G", spec_code, re.IGNORECASE)
    if match:
        row["数量"] = quantity * (int(match.group(1)) / 500)
        row["规格编码"] = "YZ-500G"
        return row

    # FZJ-100\+500
    if re.search(r"FZJ-100\+500", spec_code, re.IGNORECASE):
        row["规格编码"] = "YZ-500G"
        row["备注"] = (
            row["备注"] + " 加1包腐竹卷" if pd.notna(row["备注"]) else "加1包腐竹卷"
        )
        return row

    if re.search(r"方片型边角料,3000克（共6包）", str(row["规格名称"]), re.IGNORECASE):
        row["规格编码"] = "BJL-F-500g"
        row["数量"] = quantity * 6
        return row

    return row


def pdd_mark_combined_orders_old(dataframe):
    """
    Marks combined orders in the '备注' column with "!!!合并订单!!!".
    Combined orders are identified by having the same '运单号'.

    Parameters:
        - dataframe: The input dataframe with shipment data

    Returns:
        - Processed dataframe with marked combined orders
    """
    if dataframe.empty:
        return pd.DataFrame()
    # Check if the dataframe has the required column
    if "运单号" not in dataframe.columns:
        raise ValueError("The input dataframe does not contain the '运单号' column.")

    # Find duplicated '运单号' entries
    duplicated_express_numbers = dataframe[dataframe["运单号"].duplicated(keep=False)]

    # Mark these orders in the '备注' column
    dataframe.loc[duplicated_express_numbers.index, "备注"] = dataframe.loc[
        duplicated_express_numbers.index, "备注"
    ].apply(lambda x: "!!!合并订单!!!" if pd.isna(x) else x + " !!!合并订单!!!")

    return dataframe


def pdd_mark_combined_orders(dataframe):
    """
    在“备注”列中标记合并订单，通过在备注开头附加格式化字符串“（合并订单：订单号1，订单号2，……）”。
    通过相同的“运单号”来识别合并订单。

    参数:
        - dataframe: 包含运输数据的输入数据帧

    返回:
        - 标记了合并订单的处理过的数据帧
    """
    if dataframe.empty:
        return pd.DataFrame()
    # 检查数据帧是否包含必需的列
    if "运单号" not in dataframe.columns or "订单号" not in dataframe.columns:
        raise ValueError("输入的数据帧中缺少 '运单号' 或 '订单号' 列。")

    # 找到重复的“运单号”条目
    duplicated_express_numbers = dataframe[dataframe["运单号"].duplicated(keep=False)]

    # 对于每个重复的运单号，将其对应的所有订单号提取出来，并格式化为字符串
    combined_orders = duplicated_express_numbers.groupby("运单号")["订单号"].apply(
        lambda x: f"（合并订单：{', '.join(x)}）"
    )

    # 遍历每个合并的订单，更新对应行的“备注”列
    for express_number, orders_str in combined_orders.items():
        # 找到与当前运单号匹配的行的索引
        index_to_update = dataframe[dataframe["运单号"] == express_number].index
        # 在“备注”列的开头添加合并订单的字符串
        dataframe.loc[index_to_update, "备注"] = dataframe.loc[
            index_to_update, "备注"
        ].apply(lambda x: orders_str + ("" if pd.isna(x) else f" {x}"))

    return dataframe


def pdd_transform_shipment_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms the shipment data according to the specified requirements.

    Args:
    - df (pd.DataFrame): Original shipment data dataframe.

    Returns:
    - pd.DataFrame: Transformed shipment data.
    """
    if df.empty:
        return pd.DataFrame()
    # Extract date from "发货时间"
    df["日期"] = pd.to_datetime(df["发货时间"]).dt.strftime("%Y/%m/%d")

    # Extract province from "省/市/区"
    df["省份"] = df["省/市/区"].str.split("/").str[0]

    # Convert "支付金额" to currency
    df["实收"] = df["实收"].str.replace("￥", "").astype(float)

    # Set 发货件数 based on the "备注" column
    df["发货件数"] = 1
    merged_order_indices = df[
        df["备注"].astype(str).str.contains("!!!合并订单!!!", na=False)
    ].index
    for idx in merged_order_indices[1::2]:
        df.at[idx, "发货件数"] = 0

    # Map "规格编码" to "商品名称/简称"
    product_name_map = {
        "YZ-500G": "油炸腐竹500g",
        "S-BJ-500": "1斤装边角料",
        "QPZ-2500G": "切片竹2500g",
        "BJL-F-500g": "边角料500g",
        "FZP-500g": "边角料500g",
        "FZP-500G": "边角料500g",
        "XT-500G": "边角料500g",
        "BJL-400G": "边角料400g",
        "XPZ-240G": "小片竹240g",
        "XPZ-5000G": "小片竹10斤",
        "YZ-350G": "油炸腐竹350g",
        "FZJ-100G": "腐竹卷100g",
        "BJL-C-300G": "边角料300g",
        "CP-500G": "边角料500g",
        "CP-500g": "边角料500g",
        "FZ-240G": "小片竹240g",
        "Z-QPZ-500G": "1斤装油炸切片竹",
        "FZ-125G": "小片竹125g",
        "XPZ-125G": "小片竹125g",
        "XPZ-500G": "小片竹500g",
        "XLJ-100G": "响铃卷100g",
        "XLJ-10J-100G": "响铃卷100g",
        "XLJ-8J-100G": "响铃卷100g",
        "ZFZ-500G": "油炸腐竹500g",
        "FZ-Pi-500G": "边角料500g",
        "BJL-500g": "边角料500g",
        "XPZ-500g*1袋": "小片竹500g",
        "YZCP-500g": "油炸腐竹500g",
        "腐竹皮500g*1袋": "边角料500g",
        "腐竹皮500g*2袋": "边角料500g",
        "腐竹皮500g": "边角料500g",
        "响铃卷": "响铃卷100g",
        "油炸腐竹200g": "油炸腐竹200g",
        "XPZ-125g": "小片竹125g",
        "XPZ-500g": "小片竹500g",
        "腐竹段250g": "小片竹250g",
        "腐竹碎片1000g": "腐竹碎片1000g",
        "油炸腐竹片250g": "油炸切片竹250g",
        "油炸腐竹片500g": "油炸切片竹500g",
        "原味腐竹-125g": "小片竹125g",
        "原味腐竹-500g": "小片竹500g",
        "FZSP-1000G": "腐竹碎片1000g",
        "大片油炸腐竹次品500g": "油炸腐竹500g",
        "YZCP500g": "油炸腐竹500g",
        "桶装响铃卷": "桶装响铃卷",
        "响铃卷1桶": "桶装响铃卷",
        "兰花干边角料200g": "兰花干边角料200g",
        "兰花干边角料250g": "兰花干边角料250g",
        "兰花干边角料500g": "兰花干边角料500g",
        "油炸豆腐条200g": "油炸豆腐条200g",
        "DG-6*13-24": "6×13兰花干",
        "DG-CP-500g": "兰花干次品500g",
        "DG6*10-112": "6×10兰花干",
        "DG6*10-12": "6×10兰花干",
        "DG6*10-24": "6×10兰花干",
        "DG6*10-30": "6×10兰花干",
        "DG6*14-112": "6×13兰花干",
        "DG6*14-12": "6×13兰花干",
        "DG6*14-24": "6×13兰花干",
        "DG6*14-30": "6×13兰花干",
        "DG6*14-60": "6×13兰花干",
        "JHP【6*10】-06*02": "6×10兰花干",
        "JHP【6*10】-06*04": "6×10兰花干",
        "JHP【6*10】-06*05": "6×10兰花干",
        "JHP【6*10】-06*06": "6×10兰花干",
        "JHP【6*10】-06*10": "6×10兰花干",
        "JHP【6*10】-06*19": "6×10兰花干",
        "JHP【6*10】-06*20": "6×10兰花干",
        "JHP【6*10】-112": "6×10兰花干",
        "JHP【6*10】-12": "6×10兰花干",
        "JHP【6*10】-24": "6×10兰花干",
        "JHP【6*10】-30": "6×10兰花干",
        "JHP【6*10】-60": "6×10兰花干",
        "JHP【6*13】-06*02": "6×13兰花干",
        "JHP【6*13】-06*04": "6×13兰花干",
        "JHP【6*13】-06*05": "6×13兰花干",
        "JHP【6*13】-06*06": "6×13兰花干",
        "JHP【6*13】-06*10": "6×13兰花干",
        "JHP【6*13】-06*19": "6×13兰花干",
        "JHP【6*13】-06*20": "6×13兰花干",
        "JHP-500g": "兰花干次品500g",
        "PS-1000g": "兰花干次品1000g",
        "PS-2500g": "兰花干次品2500g",
        "PS-500g": "兰花干次品500g",
        "PS-PL-1000g": "兰花干碎品1000g",
        "PS-PL-2500g": "兰花干碎品2500g",
        "PS-PL-500g": "兰花干碎品500g",
        "油炸豆腐条400g*1": "油炸豆腐条400g",
        "油炸豆腐条400g": "油炸豆腐条400g",
        
    }
    df["商品名称/简称"] = df["规格编码"].map(product_name_map)
    df.loc[df["店铺名称"] == "桂香园腐竹", "商品名称/简称"] = df.loc[
        df["店铺名称"] == "桂香园腐竹", "商品名称/简称"
    ].replace("5斤装切片竹", "切片竹2500g")

    # Select only the required columns for the output
    result_df = df.rename(
        columns={
            "店铺名称": "店铺",
            "订单号": "订单编号",
            "快递": "快递公司",
            "运单号": "快递单号",
            "数量": "商品数量",
            "收件人": "收货人",
        }
    )[
        [
            "日期",
            "订单编号",
            "店铺",
            "收货人",
            "省份",
            "快递公司",
            "快递单号",
            "商品数量",
            "发货件数",
            "实收",
            "商品名称/简称",
            "规格编码",
            "备注",
        ]
    ]

    return result_df


def save_dataframe_to_excel(df: pd.DataFrame, default_name: str = "exported_data.xlsx"):
    # Initialize a root window but hide it (used for filedialog)
    root = Tk()
    root.withdraw()

    # Get the current user's desktop path
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    # File save dialog
    save_path = filedialog.asksaveasfilename(
        initialdir=desktop_path,
        title="Save as",
        defaultextension=".xlsx",
        filetypes=(("Excel files", "*.xlsx"), ("All files", "*.*")),
    )

    # If no path is provided (i.e., user closes the dialog), use the default path on the desktop
    if not save_path:
        save_path = os.path.join(desktop_path, default_name)

    # Save the dataframe to the specified (or default) path
    df.to_excel(save_path, index=False)

    print(f"File saved at: {save_path}")

    return save_path


def fhd_parse_wangjun_order(remark: str) -> Tuple[str, int]:
    product_name = ""
    quantity = 1
    if "2500g" in remark or "切片" in remark:
        product_name = "5斤装切片竹"
    elif "500g" in remark.lower():
        product_name = "1斤装油炸腐竹"
    if not product_name:
        return ("未知商品", 0)
    quantity_match = re.search(r"\* *(\d+)", remark)
    if quantity_match:
        quantity = int(quantity_match.group(1))
    else:
        quantity_match = re.search(r"(\d+)包", remark)
        if quantity_match:
            quantity = int(quantity_match.group(1))

    return (product_name, quantity)


def fhd_analyze_single_product_line(product_line: str) -> Tuple[str, int]:
    total_quantity = 0
    products = product_line.split(";")
    for product in products:
        if "买家秀征集活动" in product:
            continue
        desc, quantity = product.rsplit(",", 1)
        quantity = int(quantity)
        if "口味:促销款500g袋装" in desc:
            product_name = "1斤装油炸腐竹"
        elif "口味:划算商用5斤（5包装）" in desc:
            product_name = "1斤装油炸腐竹"
            quantity *= 5
        elif (
            "柳州螺蛳粉专用配菜薄片可油炸腐竹豆腐皮干货厂家商用思家腐竹" in desc
            or "思家螺蛳粉腐竹散装未油炸腐竹配菜豆皮干货厂家商用整箱5斤" in desc
        ):
            product_name = "5斤装切片竹"
        else:
            product_name = "1斤装油炸腐竹"
        total_quantity += quantity
    return (product_name, total_quantity)


def fhd_process_shipping_data(input_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process the shipping data according to the user's requirements.

    Parameters:
        input_df (DataFrame): The original shipping data.

    Returns:
        DataFrame: The processed shipping data.
    """
    if input_df.empty:
        return pd.DataFrame()

    # 保留指定的列
    columns_to_keep = [
        "打印时间",
        "店铺",
        "收件人姓名",
        "所在省份",
        "寄件人姓名",
        "快递公司",
        "运单号",
        "主订单编号",
        "商品信息",
        "实付价格",
        "卖家备注",
    ]
    processed_df = input_df[columns_to_keep].copy()

    # 分析订单
    product_list = []
    quantity_list = []
    order_id_list = []
    shop_name_list = []

    for _, row in processed_df.iterrows():
        if row["寄件人姓名"] == "王君":
            product, quantity = fhd_parse_wangjun_order(row["卖家备注"])
            order_id = ""
            shop_name = "微信"
        elif len(str(row["主订单编号"])) == 32:
            product, quantity = "", 0
            order_id = ""
            shop_name = ""
        else:
            product, quantity = fhd_analyze_single_product_line(row["商品信息"])
            order_id = row["主订单编号"]
            shop_name = row["店铺"]

        product_list.append(product)
        quantity_list.append(quantity)
        order_id_list.append(order_id)
        shop_name_list.append(shop_name)

    # 添加新列并更新主订单编号
    processed_df["商品名称"] = product_list
    processed_df["数量"] = quantity_list
    processed_df["主订单编号"] = order_id_list
    processed_df["店铺"] = shop_name_list

    return processed_df


def fhd_transform_shipping_data_to_desired_format(
    input_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Transform the shipping data to the desired format without execution.

    Parameters:
        input_df (DataFrame): The original shipping data.

    Returns:
        DataFrame: The transformed shipping data in the desired format.
    """
    if input_df.empty:
        return pd.DataFrame()

    # 日期转换
    input_df["日期"] = pd.to_datetime(input_df["打印时间"]).dt.strftime("%Y/%m/%d")

    # 订单编号
    input_df["订单编号"] = input_df["主订单编号"]

    # 发货件数
    def calculate_shipments(remark: str) -> int:
        if pd.isna(remark):
            return 1
        tracking_numbers = re.findall(r"YT[0-9]+", remark)
        return len(tracking_numbers) if tracking_numbers else 1

    input_df["发货件数"] = input_df["卖家备注"].apply(calculate_shipments)

    # 实收
    input_df["实收"] = pd.to_numeric(input_df["实付价格"], errors="coerce")

    # 商品名称/简称 与 规格编码
    mapping = {
        "1斤装油炸腐竹": "YZ-500G",
        "1斤装边角料": "S-BJ-500",
        "切片竹2500g": "QPZ-2500G",
        "5斤装切片竹": "QPZ-2500G",
        "边角料500g": "BJL-F-500g",
        "边角料400g": "BJL-400G",
        "小片竹240g": "XPZ-240G",
        "油炸腐竹350g": "YZ-350G",
        "腐竹卷100g": "FZJ-100G",
        "边角料300g": "BJL-C-300G",
    }

    def get_spec_code(row) -> str:
        if row["店铺"] == "桂香园腐竹" and row["商品名称"] == "5斤装切片竹":
            return "QPZ-2500G"
        return mapping.get(row["商品名称"], "未知")

    input_df["规格编码"] = input_df.apply(get_spec_code, axis=1)

    # 选择和重命名列
    transformed_df = input_df.rename(
        columns={
            "店铺": "店铺",
            "收件人姓名": "收货人",
            "所在省份": "省份",
            "快递公司": "快递公司",
            "运单号": "快递单号",
            "数量": "商品数量",
            "卖家备注": "备注",
            "商品名称": "商品名称/简称",
        }
    )

    selected_columns = [
        "日期",
        "订单编号",
        "店铺",
        "收货人",
        "省份",
        "快递公司",
        "快递单号",
        "商品数量",
        "发货件数",
        "实收",
        "商品名称/简称",
        "规格编码",
        "备注",
    ]
    transformed_df = transformed_df[selected_columns]

    transformed_df = deduplicate_by_order_id_alternative(transformed_df)

    transformed_df = replace_column_value(
        transformed_df, "店铺", "tb489621088", "思家食品工厂"
    )
    transformed_df = replace_column_value(
        transformed_df, "店铺", "tb3931904819", "泰昌美腐竹工厂"
    )

    transformed_df["订单编号"] = transformed_df["订单编号"].astype(str)

    return transformed_df


def deduplicate_by_order_id_alternative(input_df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate the DataFrame based on the '订单编号' column while keeping rows where '订单编号' is empty.

    Parameters:
        input_df (DataFrame): The original DataFrame with potential duplicates.

    Returns:
        DataFrame: The deduplicated DataFrame.
    """
    # 分离出'订单编号'为空和不为空的两部分
    df_with_order_id = input_df[input_df["订单编号"] != ""]
    df_without_order_id = input_df[input_df["订单编号"] == ""]

    # 对'订单编号'不为空的部分去重
    df_with_order_id_deduplicated = df_with_order_id.drop_duplicates(
        subset=["订单编号"], keep="first"
    )

    # 合并两部分
    final_df = pd.concat(
        [df_with_order_id_deduplicated, df_without_order_id], ignore_index=True
    )

    return final_df


def replace_column_value(
    input_df: pd.DataFrame, column: str, search_str: str, replace_str: str
) -> pd.DataFrame:
    """
    Replace occurrences of a search string in the '店铺' column with a replacement string.

    Parameters:
        input_df (DataFrame): The original DataFrame.
        search_str (str): The string to search for in the '店铺' column.
        replace_str (str): The string to replace the search string with.

    Returns:
        DataFrame: The DataFrame with replaced values in the '店铺' column.
    """
    output_df = input_df.copy()
    output_df[column] = output_df[column].replace(search_str, replace_str)
    return output_df


def extract_product_info(line: str) -> Tuple[str, int, float]:
    """
    Extracts product information from a given line.

    Parameters:
        line (str): A string containing product information.

    Returns:
        Tuple[str, int, float]: A tuple containing the product's SUK, quantity, and actual price.
    """
    # Split the line by "；" to get individual pieces of information
    segments = line.split("；")

    # Initialize variables to hold the desired information
    product_suk = ""
    product_quantity = 0
    product_price = 0.0
    order_id = ""
    remark = ""

    for segment in segments:
        if "商品SUK：" in segment:
            product_suk = (
                segment.split("：")[1].strip() if segment.split("：")[1].strip() else ""
            )
        elif "商品数量：" in segment:
            product_quantity = (
                int(segment.split("：")[1].strip())
                if segment.split("：")[1].strip()
                else 0
            )
        elif "商品实付价格：" in segment:
            product_price = (
                float(segment.split("：")[1].strip())
                if segment.split("：")[1].strip()
                else 0.0
            )
        elif "订单编号：" in segment:
            order_id = (
                segment.split("：")[1].strip() if segment.split("：")[1].strip() else ""
            )
        elif "卖家备注：" in segment:
            remark = (
                segment.split("：")[1].strip() if segment.split("：")[1].strip() else ""
            )

    return (product_suk, product_quantity, product_price, order_id, remark)


def extract_multiple_products_info(cell_content: str) -> List[Tuple[str, int, float]]:
    products_info = []
    lines = cell_content.strip().split("\n")
    for line in lines:
        if line.strip():
            product_info = extract_product_info(line)
            products_info.append(product_info)
    return products_info


# 商品SUK与商品名称/简称、规格编码、规格数量的对应关系
suk_mapping = {
    "3盒实惠装【76%选择】": ("腐竹卷100g", "FZJ-100G", 3),
    "方片形500g": ("边角料500g", "BJL-F-500g", 1),
    "方片形1500g（3袋）": ("边角料500g", "BJL-F-500g", 3),
    "油炸腐竹700g（2包）": ("油炸腐竹350g", "YZ-350G", 2),
    "油炸腐竹1750g（5包）": ("油炸腐竹350g", "YZ-350G", 5),
    "长条形300g": ("边角料300g", "BJL-C-300g", 1),
    "油炸腐竹1400g（4包）": ("油炸腐竹350g", "YZ-350G", 4),
    "油炸腐竹350g": ("油炸腐竹350g", "YZ-350G", 1),
    "方片形2500g（5袋）": ("边角料500g", "BJL-F-500g", 5),
    "【15斤】泰昌美4⨉4切片腐竹三包": ("切片竹2500g", "QPZ-2500G", 3),
    "【30斤】泰昌美4⨉4切片腐竹六包": ("切片竹2500g", "QPZ-2500G", 6),
    "【5斤】泰昌美4⨉4切片腐竹一包": ("切片竹2500g", "QPZ-2500G", 1),
    "6包整箱优惠装（未炸整箱）": ("切片竹2500g", "QPZ-2500G", 6),
    "1包试用装（5斤未炸）": ("切片竹2500g", "QPZ-2500G", 1),
    "【10斤】泰昌美4⨉4切片腐竹二包": ("切片竹2500g", "QPZ-2500G", 2),
    "方片形1000g（2袋）": ("边角料500g", "BJL-F-500g", 2),
    "工厂直发，量大批发请联系": ("切片竹2500g", "QPZ-2500G", 1),
    "油炸腐竹1050g（3包）": ("油炸腐竹350g", "YZ-350G", 3),
    "【5斤】泰昌美切片竹一包5斤": ("切片竹2500g", "QPZ-2500G", 1),
    "【10斤】泰昌美切片竹两包10斤": ("切片竹2500g", "QPZ-2500G", 2),
    "【15斤】泰昌美切片竹三包15斤": ("切片竹2500g", "QPZ-2500G", 3),
    "【20斤】泰昌美切片竹四包20斤": ("切片竹2500g", "QPZ-2500G", 4),
    "【25斤】泰昌美切片竹五包25斤": ("切片竹2500g", "QPZ-2500G", 5),
    "【30斤】泰昌美切片竹六包30斤": ("切片竹2500g", "QPZ-2500G", 6),
    "1盒试用装【不划算】": ("腐竹卷100g", "FZJ-100G", 1),
    "一袋无盐腐竹（240g）": ("小片竹240g", "XPZ-240G", 1),
    "一袋无盐腐竹（240g⨉1）": ("小片竹240g", "XPZ-240G", 1),
    "二袋无盐腐竹（240g⨉2）": ("小片竹240g", "XPZ-240G", 2),
    "三袋无盐腐竹（240g⨉3）": ("小片竹240g", "XPZ-240G", 3),
    "四袋无盐腐竹（240g⨉4）": ("小片竹240g", "XPZ-240G", 4),
    "五袋无盐腐竹（240g⨉5）": ("小片竹240g", "XPZ-240G", 5),
    "1包（5斤）": ("切片竹2500g", "QPZ-2500G", 1),
    "2包（共10斤）": ("切片竹2500g", "QPZ-2500G", 2),
    "3包（共15斤）": ("切片竹2500g", "QPZ-2500G", 3),
    "4包（共20斤）": ("切片竹2500g", "QPZ-2500G", 4),
    "5包（共25斤）": ("切片竹2500g", "QPZ-2500G", 5),
    "6包（共30斤）": ("切片竹2500g", "QPZ-2500G", 6),
    "头层腐竹240g": ("小片竹240g", "XPZ-240G", 1),
    "500克（净重无干燥剂）": ("小片竹500g", "XPZ-500G", 1),
    "125克（小包装试吃）": ("小片竹125g", "XPZ-125G", 1),
    "两包125克（共250克）": ("小片竹125g", "XPZ-125G", 2),
    "两包500克（共1000克）": ("小片竹500g", "XPZ-500G", 2),
    "10斤": ("小片竹10斤", "XPZ-5000G", 1),
    "响铃卷（1盒/10卷）": ("响铃卷100g", "XLJ-100G", 1),
    "响铃卷（2盒/20卷）": ("响铃卷100g", "XLJ-100G", 2),
    "响铃卷（3盒/30卷）": ("响铃卷100g", "XLJ-100G", 3),
    "响铃卷（4盒/40卷）": ("响铃卷100g", "XLJ-100G", 4),
    "响铃卷（8盒/80卷）": ("响铃卷100g", "XLJ-100G", 8),
    "响铃卷（12盒/120卷）": ("响铃卷100g", "XLJ-100G", 12),
    "12盒（共120卷）": ("响铃卷100g", "XLJ-100G", 12),
    "26盒（共260卷）": ("响铃卷100g", "XLJ-100G", 26),
    "48盒（共480卷）": ("响铃卷100g", "XLJ-100G", 48),
    "大片油炸腐竹（200克）*1包": ("油炸腐竹200g", "", 1),
    "大片油炸腐竹（200克）*2包": ("油炸腐竹200g", "", 2),
    "大片油炸腐竹（200克）*3包": ("油炸腐竹200g", "", 3),
    "大片油炸腐竹（200克）*4包": ("油炸腐竹200g", "", 4),
    "大片油炸腐竹（200克）*5包": ("油炸腐竹200g", "", 5),
    "【尝鲜】响铃卷*一盒（10卷）": ("响铃卷100g", "", 1),
    "【划算】响铃卷*二盒（20卷）": ("响铃卷100g", "", 2),
    "【推荐】响铃卷*三盒（30卷）": ("响铃卷100g", "", 3),
    "【回购】响铃卷*四盒（40卷）": ("响铃卷100g", "", 4),
    "【囤货】响铃卷*九盒（90卷）": ("响铃卷100g", "", 9),
    "【试用】螺蛳粉专用腐竹 * 1袋（五斤）": ("切片竹2500g", "", 1),
    "【划算】螺蛳粉专用腐竹 * 2袋（十斤）": ("切片竹2500g", "", 2),
    "【推荐】螺蛳粉专用腐竹 * 3袋（十五斤）": ("切片竹2500g", "", 3),
    "【囤货】螺蛳粉专用腐竹 * 4袋（二十斤）": ("切片竹2500g", "", 4),
    "【商用】螺蛳粉专用腐竹 * 5袋（二十五斤）": ("切片竹2500g", "", 5),
    "【批发】螺蛳粉专用腐竹 * 6袋（三十斤）": ("切片竹2500g", "", 6),
    "大片油炸腐竹次品*一袋（350g）": ("油炸腐竹350g", "", 1),
    "大片油炸腐竹次品*两袋": ("油炸腐竹350g", "", 2),
    "大片油炸腐竹次品*三袋": ("油炸腐竹350g", "", 3),
    "大片油炸腐竹次品*四袋": ("油炸腐竹350g", "", 4),
    "大片油炸腐竹次品*五袋": ("油炸腐竹350g", "", 5),
    "大片油炸腐竹次品*十袋": ("油炸腐竹350g", "", 10),
    "手工腐竹*一袋（125g）": ("小片竹125g", "", 1),
    "手工腐竹*一袋（500g）": ("小片竹500g", "", 1),
    "手工腐竹*两袋（1000g）": ("小片竹500g", "", 2),
    "手工腐竹*三袋（1500g）": ("小片竹500g", "", 3),
    "【尝鲜】腐竹边角料*500克": ("边角料500g", "", 1),
    "【划算】腐竹边角料*1000克": ("边角料500g", "", 2),
    "【推荐】腐竹边角料*1500克": ("边角料500g", "", 3),
    "【囤货】腐竹边角料*2500克": ("边角料500g", "", 5),
    "大片油炸腐竹次品500g*1包": ("油炸腐竹500g", "", 1),
    "大片油炸腐竹次品500g*2包": ("油炸腐竹500g", "", 2),
    "大片油炸腐竹次品500g*3包": ("油炸腐竹500g", "", 3),
    "大片油炸腐竹次品500g*4包": ("油炸腐竹500g", "", 4),
    "大片油炸腐竹次品500g*5包": ("油炸腐竹500g", "", 5),
    "【汤汁收割者】手工响铃卷10卷*1盒": ("响铃卷100g", "", 1),
    "【Q弹嫩滑】手工腐竹125g*1袋": ("小片竹125g", "", 1),
    "【吸汁劲道】手工腐竹段250g*1袋": ("腐竹段250g", "", 1),
    "【配菜加量】螺蛳粉腐竹片250g*1袋": ("油炸切片竹250g", "", 1),
    "【香脆可口】巴掌大油炸腐竹200g*1袋": ("油炸腐竹200g", "", 1),
    "【吸汁王炸组合】手工响铃卷*1盒+巴掌大油炸腐竹*一袋": (
        "响铃卷100g，油炸腐竹200g",
        "",
        2,
    ),
    "【鲜香嫩滑】手工腐竹*1袋+腐竹段*1袋": ("小片竹125g，腐竹段250g", "", 2),
    "【螺蛳粉配菜全家福】巴掌大油炸腐竹*1袋+手工响铃卷*1盒+螺蛳粉腐竹片*1袋": (
        "油炸腐竹200g，响铃卷100g,油炸切片竹250g",
        "",
        3,
    ),
    "黄金响铃卷100g*1盒": ("响铃卷100g", "", 1),
    "黄金响铃卷100g*2盒": ("响铃卷100g", "", 2),
    "黄金响铃卷100g*3盒": ("响铃卷100g", "", 3),
    "黄金响铃卷100g*4盒": ("响铃卷100g", "", 4),
    "黄金响铃卷100g*9盒": ("响铃卷100g", "", 9),
    "大片油炸腐竹次品500g*1袋": ("油炸腐竹500g", "", 1),
    "大片油炸腐竹次品500g*2袋": ("油炸腐竹500g", "", 2),
    "大片油炸腐竹次品500g*3袋": ("油炸腐竹500g", "", 3),
    "大片油炸腐竹次品500g*4袋": ("油炸腐竹500g", "", 4),
    "大片油炸腐竹次品500g*5袋": ("油炸腐竹500g", "", 5),
    "腐竹边角料500g*1袋": ("边角料500g", "", 1),
    "腐竹边角料500g*2袋": ("边角料500g", "", 2),
    "腐竹边角料500g*3袋": ("边角料500g", "", 3),
    "腐竹边角料500g*5袋": ("边角料500g", "", 5),
    "【汤汁收割者】手工响铃卷100g*1盒": ("响铃卷100g", "", 1),
    "【配菜加量】螺蛳粉大腐竹片250g*1袋": ("油炸切片竹250g", "", 1),
    "【吸汁王炸组合】手工响铃卷*10卷100g*1盒+巴掌大油炸腐竹200g*1袋": (
        "响铃卷100g，油炸腐竹200g",
        "",
        2,
    ),
    "【鲜香嫩滑】手工腐竹125g*1袋+手工腐竹段200g*1袋": (
        "小片竹125g，腐竹段250g",
        "",
        2,
    ),
    "【螺蛳粉配菜全家福】巴掌大油炸腐竹200g*1袋+手工响铃卷100g*1盒+螺蛳粉大腐竹片250g*1袋": (
        "油炸腐竹200g，响铃卷100g,油炸切片竹250g",
        "",
        3,
    ),
    "大片油炸腐竹200g*1袋": ("油炸腐竹200g", "", 1),
    "大片油炸腐竹200g*2袋": ("油炸腐竹200g", "", 2),
    "大片油炸腐竹200g*3袋": ("油炸腐竹200g", "", 3),
    "大片油炸腐竹200g*4袋": ("油炸腐竹200g", "", 4),
    "大片油炸腐竹200g*5袋": ("油炸腐竹200g", "", 5),
    "手工腐竹125g*1袋": ("小片竹125g", "", 1),
    "手工腐竹500g*1袋": ("小片竹500g", "", 1),
    "手工腐竹500g*2袋": ("小片竹500g", "", 2),
    "手工腐竹500g*3袋": ("小片竹500g", "", 3),
    "【试用】螺蛳粉专用腐竹 5斤*1袋": ("切片竹2500g", "", 1),
    "【划算】螺蛳粉专用腐竹 5斤*2袋": ("切片竹2500g", "", 2),
    "【推荐】螺蛳粉专用腐竹 5斤*3袋": ("切片竹2500g", "", 3),
    "【囤货】螺蛳粉专用腐竹 5斤*4袋": ("切片竹2500g", "", 4),
    "【商用】螺蛳粉专用腐竹 5斤*5袋": ("切片竹2500g", "", 5),
    "【批发】螺蛳粉专用腐竹 5斤*6袋": ("切片竹2500g", "", 6),
    "大片油炸腐竹（次品）350g*1袋": ("油炸腐竹350g", "", 1),
    "大片油炸腐竹350g*1袋": ("油炸腐竹350g", "", 1),
    "大片油炸腐竹350g*2袋": ("油炸腐竹350g", "", 2),
    "大片油炸腐竹350g*3袋": ("油炸腐竹350g", "", 3),
    "大片油炸腐竹350g*4袋": ("油炸腐竹350g", "", 4),
    "大片油炸腐竹350g*5袋": ("油炸腐竹350g", "", 5),
    "大片油炸腐竹350g*10袋": ("油炸腐竹350g", "", 10),
    "腐竹皮500g*1袋": ("边角料500g", "", 1),
    "腐竹皮500g*2袋": ("边角料500g", "", 2),
    "腐竹皮500g*3袋": ("边角料500g", "", 3),
    "腐竹皮500g*4袋": ("边角料500g", "", 4),
    "腐竹皮500g*5袋": ("边角料500g", "", 5),
    "腐竹皮500g*6袋": ("边角料500g", "", 6),
    "YZCP-500g*1": ("油炸腐竹500g", "", 1),
    "YZCP-500g*2": ("油炸腐竹500g", "", 2),
    "YZCP-500g*3": ("油炸腐竹500g", "", 3),
    "YZCP-500g*4": ("油炸腐竹500g", "", 4),
    "YZCP-500g*5": ("油炸腐竹500g", "", 5),
    "BJL-500g*1": ("边角料500g", "", 1),
    "BJL-500g*2": ("边角料500g", "", 2),
    "BJL-500g*3": ("边角料500g", "", 3),
    "BJL-500g*4": ("边角料500g", "", 4),
    "BJL-500g*5": ("边角料500g", "", 5),
    "TCM-2500g*1": ("切片竹2500g", "", 1),
    "TCM-2500g*2": ("切片竹2500g", "", 2),
    "TCM-2500g*3": ("切片竹2500g", "", 3),
    "TCM-2500g*4": ("切片竹2500g", "", 4),
    "TCM-2500g*5": ("切片竹2500g", "", 5),
    "TCM-2500g*6": ("切片竹2500g", "", 6),
    "响铃卷*1": ("响铃卷100g", "", 1),
    "响铃卷*2": ("响铃卷100g", "", 2),
    "响铃卷*3": ("响铃卷100g", "", 3),
    "响铃卷*4": ("响铃卷100g", "", 4),
    "响铃卷*5": ("响铃卷100g", "", 5),
    "响铃卷*6": ("响铃卷100g", "", 6),
    "XPZ-125g*1袋": ("小片竹125g", "", 1),
    "XPZ-500g*1袋": ("小片竹500g", "", 1),
    "XPZ-500g*2袋": ("小片竹500g", "", 2),
    "XPZ-500g*3袋": ("小片竹500g", "", 3),
    "XPZ-500g*4袋": ("小片竹500g", "", 4),
    "油炸腐竹200g*1": ("油炸腐竹200g", "", 1),
    "油炸腐竹200g*2": ("油炸腐竹200g", "", 2),
    "油炸腐竹200g*3": ("油炸腐竹200g", "", 3),
    "油炸腐竹200g*4": ("油炸腐竹200g", "", 4),
    "油炸腐竹200g*5": ("油炸腐竹200g", "", 5),
    "【尝鲜】腐竹皮边角料500g*1袋": ("腐竹皮500g", "", 1),
    "【划算】腐竹皮边角料500g*2袋": ("腐竹皮500g", "", 2),
    "【推荐】腐竹皮边角料500g*3袋": ("腐竹皮500g", "", 3),
    "【聚餐】腐竹皮边角料500g*4袋": ("腐竹皮500g", "", 4),
    "【批发】腐竹皮边角料500g*5袋": ("腐竹皮500g", "", 5),
    "【商用】腐竹皮边角料500g*6袋": ("腐竹皮500g", "", 6),
    "原味腐竹*一袋（125g）": ("小片竹125g", "", 1),
    "【尝试】螺蛳粉专用腐竹 * 1斤装": ("切片竹500g", "", 1),
    "原味腐竹*一袋（500g）": ("小片竹500g", "", 1),
    "原味腐竹*两袋（1000g）": ("小片竹500g", "", 2),
    "大片油炸腐竹20g*6盒": ("油炸腐竹20g", "", 6),
    "大片油炸腐竹20g*10盒": ("油炸腐竹20g", "", 10),
    "大片油炸腐竹20g*20盒": ("油炸腐竹20g", "", 20),
    "大片油炸腐竹20g*30盒": ("油炸腐竹20g", "", 30),
    "大片油炸腐竹20g*6盒": ("油炸腐竹20g", "", 6),
    "大片油炸腐竹20g*10盒": ("油炸腐竹20g", "", 10),
    "大片油炸腐竹20g*20盒": ("油炸腐竹20g", "", 20),
    "大片油炸腐竹20g*30盒": ("油炸腐竹20g", "", 30),
}


def tb_process_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process a DataFrame containing Taobao orders and returns a new DataFrame with additional columns.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the original orders.

    Returns:
        pd.DataFrame: A new DataFrame with the processed orders.
    """
    if df.empty:
        return df

    # 保留用户指定的列
    columns_to_keep = [
        "订单编号",
        "快递公司",
        "运单号",
        "店铺",
        "打印时间",
        "打印类型",
        "收件人姓名",
        "省",
        "商品信息",
    ]
    df_filtered = df[columns_to_keep]

    # 创建一个新的DataFrame来存储解析后的订单信息
    new_rows = []

    # 遍历原始DataFrame，解析商品信息并添加新的列
    for index, row in df_filtered.iterrows():
        print_type = row["打印类型"]
        if print_type == "平台订单":
            multiple_products_info = extract_multiple_products_info(row["商品信息"])
            if len(multiple_products_info) > 1:
                remark = "!!!合并订单!!!"
            else:
                remark = ""
            for (
                product_suk,
                quantity,
                price,
                order_id,
                m_remark,
            ) in multiple_products_info:
                # 使用商品SUK查找商品名称/简称、规格编码和规格数量
                product_name, product_code, unit_quantity = suk_mapping.get(
                    product_suk, ("", "", 0)
                )
                actual_quantity = unit_quantity * quantity
                new_row = row.copy()
                new_row["订单编号"] = order_id
                new_row["商品名称/简称"] = product_name
                new_row["规格编码"] = product_code
                new_row["商品数量"] = actual_quantity
                new_row["实收"] = price
                new_row["备注"] = m_remark + "；" + remark if m_remark else remark
                new_rows.append(new_row)
        else:
            new_row = row.copy()
            new_row["商品名称/简称"] = ""
            new_row["规格编码"] = ""
            new_row["商品数量"] = 0
            new_row["实收"] = 0.0
            new_row["备注"] = ""
            new_rows.append(new_row)

    # pd.DataFrame(new_rows).to_excel("670.xlsx",index=False)
    # transform_to_final_format(pd.DataFrame(new_rows)).to_excel("671.xlsx",index=False)
    # handle_multiple_courier(transform_to_final_format(pd.DataFrame(new_rows))).to_excel("672.xlsx",index=False)

    # 创建一个新的DataFrame
    df_new = handle_multiple_courier(transform_to_final_format(pd.DataFrame(new_rows)))
    df_new = replace_column_value(df_new, "店铺", "tb3931904819", "泰昌美腐竹工厂")
    df_new["订单编号"] = df_new["订单编号"].astype(str)
    return df_new


def transform_to_final_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms the processed orders DataFrame into the final required format.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the processed orders.

    Returns:
        pd.DataFrame: A new DataFrame with the orders in the final required format.
    """

    # 转换 '打印时间' 列到短日期格式
    df["日期"] = pd.to_datetime(df["打印时间"]).dt.strftime("%Y/%m/%d")

    # 重命名列
    column_mapping = {
        "订单编号": "订单编号",
        "店铺": "店铺",
        "收件人姓名": "收货人",
        "省": "省份",
        "快递公司": "快递公司",
        "运单号": "快递单号",
        "商品数量": "商品数量",
        "商品名称/简称": "商品名称/简称",
        "规格编码": "规格编码",
        "实收": "实收",
        "备注": "备注",
    }
    df_final = df.rename(columns=column_mapping)

    # 计算 '发货件数' 列（因为我们拆分了具有多个商品的订单，所以发货件数对于每个订单都是1）
    df_final["发货件数"] = 1

    # 调整列的顺序
    final_columns_order = [
        "日期",
        "订单编号",
        "店铺",
        "收货人",
        "省份",
        "快递公司",
        "快递单号",
        "商品数量",
        "发货件数",
        "实收",
        "商品名称/简称",
        "规格编码",
        "备注",
    ]
    df_final = df_final[final_columns_order]

    return df_final


def consolidate_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Consolidates orders with the same order number but different tracking numbers into a single row.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the orders in the final required format.

    Returns:
        pd.DataFrame: A new DataFrame with the consolidated orders.
    """

    # 用于存储整合后的订单信息的字典
    consolidated_orders = defaultdict(list)

    # 遍历DataFrame，整合具有相同订单编号但不同快递单号的订单
    for index, row in df.iterrows():
        order_id = row["订单编号"]
        tracking_number = row["快递单号"]
        key_tuple = (order_id, row["规格编码"], row["商品数量"])

        if key_tuple in consolidated_orders:
            # 如果这个订单已经存在，更新相关信息
            existing_order = consolidated_orders[key_tuple]
            existing_order["快递单号"].append(tracking_number)
            existing_order["发货件数"] += 1
        else:
            # 如果这是一个新订单，添加到字典中
            new_order = row.copy()
            new_order["快递单号"] = [tracking_number]
            new_order["发货件数"] = 1
            consolidated_orders[key_tuple] = new_order

    # 创建一个新的DataFrame来存储整合后的订单信息
    new_rows = []
    for key_tuple, consolidated_order in consolidated_orders.items():
        new_row = consolidated_order.copy()
        new_row["快递单号"] = ", ".join(new_row["快递单号"])
        new_rows.append(new_row)

    df_consolidated = pd.DataFrame(new_rows)

    return df_consolidated


def handle_multiple_courier(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handles orders with multiple couriers in the DataFrame.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the processed orders.

    Returns:
        pd.DataFrame: A new DataFrame with orders having multiple couriers handled.
    """

    # 创建一个字典以存储具有多个快递单号的订单
    multiple_courier_dict = defaultdict(list)

    # 遍历DataFrame，查找具有多个快递单号的订单
    for index, row in df.iterrows():
        key = (row["订单编号"], row["规格编码"], row["商品数量"])
        multiple_courier_dict[key].append(row["快递单号"])

    # 创建一个新的DataFrame以存储处理后的订单信息
    new_rows = []

    # 记录已处理的订单编号，以避免重复处理
    processed_orders = set()

    # 遍历DataFrame，处理具有多个快递单号的订单
    for index, row in df.iterrows():
        key = (row["订单编号"], row["规格编码"], row["商品数量"])
        if key in processed_orders:
            continue

        # 如果一个订单有多个快递单号，合并它们并更新'发货件数'列
        if len(multiple_courier_dict[key]) > 1:
            unique_courier_numbers = list(set(multiple_courier_dict[key]))
            row["快递单号"] = ", ".join(unique_courier_numbers)
            row["发货件数"] = len(unique_courier_numbers)

        new_rows.append(row)
        processed_orders.add(key)

    # 创建一个新的DataFrame
    df_new = pd.DataFrame(new_rows)

    return df_new


def wangjun_filter_and_select_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters rows where 寄件人姓名 is '王君' and selects specific columns.

    Parameters:
        df (pd.DataFrame): The DataFrame containing the original data.

    Returns:
        pd.DataFrame: A new DataFrame with filtered rows and selected columns.
    """

    # 过滤出寄件人姓名是“王君”的行
    df_filtered = df[df["寄件人姓名"] == "王君"]

    # 选择需要保留的列
    columns_to_keep = [
        "收件人姓名",
        "收件人手机",
        "收件人电话",
        "所在省份",
        "所在城市",
        "所在地区",
        "详细地址",
        "寄件人姓名",
        "寄件人电话",
        "寄件人地址",
        "快递公司",
        "运单号",
        "实付价格",
        "卖家备注",
    ]

    df_selected = df_filtered[columns_to_keep]

    # 分析订单
    product_list = []
    quantity_list = []
    price_list = []

    for _, row in df_selected.iterrows():
        product, quantity = fhd_parse_wangjun_order(row["卖家备注"])
        product_list.append(product)
        quantity_list.append(quantity)
        # 处理实付价格...
        if product == "5斤装切片竹":
            price = 55 * quantity
        elif product == "1斤装油炸腐竹":
            # 如果quantity是1，price是11，quantity是2，price是21，quantity是3，price是31，依此类推
            price = 10 * quantity + 1
        else:
            price = 0
        price_list.append(price)

    # 添加新列并更新主订单编号
    df_selected["商品名称"] = product_list
    df_selected["数量"] = quantity_list
    df_selected["实付价格"] = price_list

    return df_selected


def calculate_shipping_cost_v3(
    yuantong_df: pd.DataFrame,
    jitui_df: pd.DataFrame,
    company: str,
    weight: float,
    province: str,
) -> Optional[float]:
    if "圆通" in str(company):
        df = yuantong_df
    elif "极兔" in str(company):
        df = jitui_df
    else:
        return None

    province_row = df[df["到达省份"].apply(lambda x: x in province)]
    if province_row.empty:
        return None

    province_row = province_row.squeeze()

    # 递归计算超过10KG的重量
    if weight > 10:
        num_full_weights = int(weight // 10)  # 计算完整10KG的包裹数量
        remaining_weight = weight % 10  # 剩余的重量
        total_cost = 0

        # 计算每个完整10KG的包裹的运费
        for _ in range(num_full_weights):
            total_cost += calculate_shipping_cost_v3(
                yuantong_df, jitui_df, company, 10, province
            )

        # 如果有剩余重量，计算剩余重量的运费
        if remaining_weight > 0:
            total_cost += calculate_shipping_cost_v3(
                yuantong_df, jitui_df, company, remaining_weight, province
            )
        return total_cost

    weight_categories = [
        ("0-1KG(元）", 1),
        ("1.01-2KG (元）", 2),
        ("2.01-3Kg(元）", 3),
        ("3.01-4KG(元）", 4),
        ("4.01-5KG(元）", 5),
        ("5.01-6Kg（元）", 6),
        ("6.01-7Kg（元）", 7),
        ("7.01-8Kg（元）", 8),
        ("8.01-9Kg（元）", 9),
        ("9.01-10Kg（元）", 10),
    ]

    for category, max_weight in weight_categories:
        if weight <= max_weight:
            return province_row[category]
    return None


# Mapping for custom box weights based on weight categories
# Here, the key represents the upper limit of the weight category in KG, and the value is the box weight in KG
custom_box_weights: Dict[float, float] = {
    1: 0.4,  # Up to 1 KG, 400g box
    2: 0.4,  # Up to 2 KG, 400g box
    # Add more categories as needed
}


def extract_weight_from_name(name: str) -> float:
    """
    Extract the weight information from the product name.

    Parameters:
    - name (str): Product name containing weight information.

    Returns:
    - float: Extracted weight in kilograms.
    """
    # Regular expression patterns for extracting weight information
    patterns = [r"(\d+\.?\d*)斤", r"(\d+\.?\d*)g"]

    for pattern in patterns:
        match = re.search(pattern, str(name))
        if match:
            weight = float(match.group(1))
            if "斤" in pattern:
                weight *= 0.5  # Convert 斤 to KG
            elif "g" in pattern:
                weight /= 1000  # Convert grams to KG
            return weight
    return 0.0  # Default weight if no pattern matches


def calculate_shipping_costs_for_df(
    df: pd.DataFrame, jitui_df, yuantong_df
) -> pd.DataFrame:
    """
    Calculate the estimated shipping costs for a DataFrame of shipments.

    Parameters:
    - df (pd.DataFrame): DataFrame containing shipment information.

    Returns:
    - pd.DataFrame: Updated DataFrame with a new column for estimated shipping costs.
    """
    estimated_costs = []

    for _, row in df.iterrows():
        # Extract necessary information from the row
        province = row.get("省份", "")
        company = row.get("快递公司", "")
        product_name = row.get("商品名称/简称", "")
        product_quantity = row.get("商品数量", 1)
        num_shipments = row.get("发货件数", 1)

        if re.search(r"\*", province):
            estimated_costs.append("")
            continue
        if num_shipments == 0:
            estimated_costs.append("")
            continue

        # Extract weight from the product name
        product_weight = extract_weight_from_name(product_name)

        # Calculate total product weight
        total_weight = product_weight * product_quantity

        # Calculate per-shipment weight
        per_shipment_weight = total_weight / num_shipments

        # Add box weight based on the per-shipment weight category
        box_weight = 0.4  # Default to 400g
        for weight_limit in sorted(custom_box_weights.keys()):
            if per_shipment_weight <= weight_limit:
                box_weight = custom_box_weights[weight_limit]
                break

        # Add box weight to the per-shipment weight
        per_shipment_weight += box_weight

        # Calculate shipping cost for one shipment
        cost_per_shipment = calculate_shipping_cost_v3(
            yuantong_df, jitui_df, company, per_shipment_weight, province
        )

        # Calculate total shipping cost
        total_cost = (
            cost_per_shipment * num_shipments if cost_per_shipment is not None else None
        )

        # Append the calculated cost to the list
        estimated_costs.append(total_cost)

    # Add the estimated costs as a new column in the DataFrame
    df["估算快递费"] = estimated_costs

    return df


# 定义函数来计算去快递费单价
def calculate_unit_price_without_shipping(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算去快递费单价（修改版）。

    参数:
        df (DataFrame): 原始的数据表，含有估算快递费、实收、商品数量等列。

    返回:
        DataFrame: 含有“商品名称/简称”和“去快递费单价”的数据表。
    """
    # 筛选出 '估算快递费' 非空的行
    filtered_df = df[df["估算快递费"].notna()]

    # 将涉及的列转换为浮点数类型
    for col in ["实收", "估算快递费", "商品数量"]:
        filtered_df.loc[:, col] = pd.to_numeric(filtered_df[col], errors="coerce")

    # 过滤掉无法转换为数值的行
    filtered_df = filtered_df.dropna(subset=["实收", "估算快递费", "商品数量"])

    # 按照 '商品名称/简称' 进行分组，并计算每组的 '实收'、'估算快递费' 和 '商品数量' 的总和
    grouped = (
        filtered_df.groupby("商品名称/简称")
        .agg({"实收": "sum", "估算快递费": "sum", "商品数量": "sum"})
        .reset_index()
    )

    # 计算去快递费单价
    grouped["去快递费单价"] = (grouped["实收"] - grouped["估算快递费"]) / grouped[
        "商品数量"
    ]

    # 返回只包含 '商品名称/简称' 和 '去快递费单价' 的数据表
    return grouped[["商品名称/简称", "去快递费单价"]]


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    对给定的DataFrame进行转换，生成一个新的DataFrame。

    参数:
    df: DataFrame - 包含原始数据的DataFrame，其列包括：
        日期, 订单编号, 店铺, 收货人, 省份, 快递公司, 快递单号, 商品数量, 发货件数, 实收, 商品名称/简称, 规格编码, 备注, 估算快递费

    返回:
    DataFrame - 转换后的DataFrame，包含以下列：
        日期, 产品名称, 数量, 金额

    处理流程:
    1. 按照 '日期' 列对数据进行分组。
    2. 在每个日期内，根据 '商品名称/简称' 再次分组。
    3. 对每个商品名称/简称分组，计算 '商品数量' 和 '实收' 的总和。
    4. 将结果汇总成新的DataFrame并返回。
    """
    # 按照 '日期' 和 '商品名称/简称' 分组，然后对 '商品数量' 和 '实收' 进行求和
    grouped = (
        df.groupby(["日期", "商品名称/简称"])
        .agg({"商品数量": "sum", "实收": "sum"})
        .reset_index()
    )

    # 重命名列以匹配输出格式
    grouped.rename(
        columns={"商品名称/简称": "产品名称", "商品数量": "数量", "实收": "金额"},
        inplace=True,
    )

    return grouped


def summarize_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    对给定的DataFrame进行处理，生成一个新的DataFrame。

    参数:
    df: DataFrame - 包含原始数据的DataFrame，其列包括：
        日期, 订单编号, 店铺, 收货人, 省份, 快递公司, 快递单号, 商品数量, 发货件数, 实收, 商品名称/简称, 规格编码, 备注, 估算快递费

    返回:
    DataFrame - 处理后的DataFrame，包含以下列：
        日期, 产品名称, 商品数量, 订单数

    处理流程:
    1. 按照 '日期' 和 '商品名称/简称' 分组。
    2. 对每个组，按照 '商品数量' 分组。
    3. 对每个 '商品数量' 计算行数，作为订单数。
    4. 将结果汇总成新的DataFrame并返回。
    """

    # 定义一个函数来处理每个分组
    def process_group(group):
        return (
            group.groupby("商品数量")
            .size()
            .reset_index(name="订单数")
            .assign(产品名称=group.name[1], 日期=group.name[0])
        )

    # 按照 '日期' 和 '商品名称/简称' 分组，并对每个组应用上面定义的函数
    result = df.groupby(["日期", "商品名称/简称"]).apply(process_group)

    # 重设索引，并只保留需要的列
    result = result.reset_index(drop=True)[["日期", "产品名称", "商品数量", "订单数"]]

    return result


def pdd_yuehuizhong(orders_df: pd.DataFrame) -> pd.DataFrame:
    # 定义商品规格与商品名称和规格包含数量的对应关系
    specification_mapping = {
        "1200g": ("边角料400g", 3),
        "1600g": ("边角料400g", 4),
        "2000g": ("边角料400g", 5),
        "2400g": ("边角料400g", 6),
        "400g": ("边角料400g", 1),
        "800g": ("边角料400g", 2),
        "薄片4*4切片竹【10斤】2包": ("切片竹2500g", 2),
        "薄片4*4切片竹【15斤】3包": ("切片竹2500g", 3),
        "薄片4*4切片竹【20斤】4包": ("切片竹2500g", 4),
        "薄片4*4切片竹【25斤】5包": ("切片竹2500g", 5),
        "薄片4*4切片竹【30斤】6包": ("切片竹2500g", 6),
        "薄片4*4切片竹【5斤】": ("切片竹2500g", 1),
        "方片型边角料,1000克(2包)": ("边角料500g", 2),
        "方片型边角料,1500克(3包)": ("边角料500g", 3),
        "方片型边角料,2500克(5包)": ("边角料500g", 5),
        "方片型边角料,500克": ("边角料500g", 1),
        "腐竹卷100g（一盒）": ("腐竹卷100g", 1),
        "腐竹卷200g（2盒）": ("腐竹卷100g", 2),
        "腐竹片-500克": ("边角料500g", 1),
        "腐竹片-两斤": ("边角料500g", 2),
        "腐竹片-三斤": ("边角料500g", 3),
        "腐竹片-五斤": ("边角料500g", 5),
        "三袋": ("小片竹240g", 3),
        "泰昌美1包（五斤）": ("切片竹2500g", 1),
        "泰昌美3包（十五斤）": ("切片竹2500g", 3),
        "一袋": ("小片竹240g", 1),
        "油炸腐竹1050g（3包）": ("油炸腐竹350g", 3),
        "油炸腐竹1750g（5包）": ("油炸腐竹350g", 5),
        "油炸腐竹350g": ("油炸腐竹350g", 1),
        "油炸腐竹700g（2包）": ("油炸腐竹350g", 2),
    }

    # 清洗数据
    # 1. 转换日期格式并过滤发货时间在2023年10月的订单
    orders_df["发货时间"] = pd.to_datetime(orders_df["发货时间"], errors="coerce")
    orders_df = orders_df[
        (orders_df["发货时间"] >= "2023-10-01") & (orders_df["发货时间"] < "2023-11-01")
    ]

    # 2. 过滤出快递单号非空的订单
    orders_df = orders_df[
        orders_df["快递单号"].notna() & (orders_df["快递单号"] != "\t")
    ]

    # 3. 提取商品名称和计算实际商品数量
    def extract_product_info(spec):
        product_name, quantity_included = specification_mapping.get(
            spec, ("未知商品", 0)
        )
        return product_name, quantity_included

    orders_df["商品名称"], orders_df["规格包含数量"] = zip(
        *orders_df["商品规格"].map(extract_product_info)
    )
    orders_df["实际商品数量"] = orders_df["规格包含数量"] * orders_df["商品数量(件)"]

    # 4. 创建新表格
    cleaned_orders_df = orders_df[
        [
            "订单号",
            "商品名称",
            "实际商品数量",
            "商家实收金额(元)",
            "发货时间",
            "售后状态",
        ]
    ].copy()

    # 处理售后状态和实收金额
    cleaned_orders_df["售后状态"] = cleaned_orders_df["售后状态"].replace(
        ["无售后或售后取消"], ""
    )
    cleaned_orders_df.loc[
        cleaned_orders_df["售后状态"].isin(["售后处理中", "退款成功"]),
        "商家实收金额(元)",
    ] = 0

    # 5. 添加店铺列
    cleaned_orders_df["店铺"] = "桂香园腐竹（拼多多）"

    # 6. 调整列顺序
    final_orders_df = cleaned_orders_df[
        [
            "店铺",
            "订单号",
            "商品名称",
            "实际商品数量",
            "商家实收金额(元)",
            "发货时间",
            "售后状态",
        ]
    ]

    # 7. 日期格式调整
    final_orders_df["发货时间"] = final_orders_df["发货时间"].dt.strftime("%Y/%m/%d")

    return final_orders_df

    # 创建一个Pandas Excel writer对象，使用xlsxwriter作为引擎
    excel_writer = pd.ExcelWriter("/mnt/data/拼多多订单数据.xlsx", engine="xlsxwriter")

    # 按商品名称分成多个sheet
    for product_name, product_group in final_orders_df.groupby("商品名称"):
        product_group.to_excel(excel_writer, sheet_name=product_name, index=False)

    return excel_writer


# def douyin(df:pd.DataFrame)->pd.DataFrame: 1147.28
