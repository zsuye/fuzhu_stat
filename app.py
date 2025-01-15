import datetime
from io import BytesIO
import locale
import platform
import shutil
import socket
import sys
import tempfile
import webbrowser
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from datetime import date, datetime
import os
import re
from typing import List, Dict, Any
import excel
import style
import logging
import sys
import os
from datetime import datetime

# 设置日志文件路径
log_dir = os.path.join(os.path.expanduser("~"), "AppLogs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_filename = os.path.join(log_dir, f"app_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# 配置日志记录
logging.basicConfig(filename=log_filename,
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

# 捕获未处理的异常并记录到日志文件
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# 示例：记录启动信息
logging.info("Application started")

os.environ["PYTHONIOENCODING"] = "UTF-8"
locale.setlocale(locale.LC_ALL, "zh_CN.UTF-8")

tmpdirname = tempfile.mkdtemp()
print(f"临时目录：{tmpdirname}")

if getattr(sys, "frozen", False):  # 如果应用被打包
    template_dir = os.path.join(sys._MEIPASS, "templates")
    static_dir = os.path.join(sys._MEIPASS, "static")
else:
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    static_dir = os.path.join(os.path.dirname(__file__), "static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)


@app.route("/")
def index():
    logging.info("Rendering index page")
    try:
        return render_template("index.html", title="电商统计工具")
    except Exception as e:
        logging.error("Error rendering index page", exc_info=True)
        return "An error occurred", 500


def save_files_to_temp_dir(file_objects: List) -> List[str]:
    temp_dir = tmpdirname
    file_paths = []
    for file_object in file_objects:
        if not file_object.filename:
            continue
        path = os.path.join(temp_dir, file_object.filename)
        file_object.save(path)
        file_paths.append(path)
    return file_paths


def save_file_to_temp_dir(file_object) -> List[str]:
    temp_dir = tmpdirname
    path = os.path.join(temp_dir, file_object.filename)
    file_object.save(path)
    return path


jitui_df = pd.read_excel(os.path.join(static_dir, "极兔价格表.xlsx"))
yuantong_df = pd.read_excel(os.path.join(static_dir, "圆通价格表.xlsx"))


@app.route("/fahuobiao", methods=["POST"])
def fahuobiao():
    pdd = save_files_to_temp_dir(request.files.getlist("pdd"))
    fhd = save_files_to_temp_dir(request.files.getlist("fhd"))
    taobao = save_files_to_temp_dir(request.files.getlist("taobao"))
    douyin = save_files_to_temp_dir(request.files.getlist("douyin"))

    pdd = excel.merge_excel_files_from_paths(pdd)
    fhd = excel.merge_excel_files_from_paths(fhd)
    taobao = excel.merge_excel_files_from_paths(taobao)
    douyin = excel.merge_excel_files_from_paths(douyin)

    pdd = pdd.apply(excel.pdd_process_spec_and_quantity, axis=1)
    pdd = excel.pdd_mark_combined_orders(pdd)
    pdd = excel.pdd_transform_shipment_data(pdd)

    fhd = excel.fhd_process_shipping_data(fhd)
    fhd = excel.fhd_transform_shipping_data_to_desired_format(fhd)

    taobao = excel.tb_process_orders(taobao)
    taobao.to_excel("taobao.xlsx",index=False)

    all = pd.concat([pdd, fhd, taobao, douyin], ignore_index=True)
    all = all.sort_values(
        by=["日期", "店铺", "规格编码", "商品数量"], ascending=[False, True, True, True]
    )
    all = excel.replace_column_value(all, "规格编码", "未知", "")
    all = excel.calculate_shipping_costs_for_df(all, jitui_df, yuantong_df)

    unit_price = excel.calculate_unit_price_without_shipping(all)

    group = excel.transform_data(all)

    group_by_number = excel.summarize_orders(all)

    current_date = datetime.now().strftime("%m月%d日")
    default_name = f"{current_date}电商发货表.xlsx"

    # return generate_excel_response(all, default_name)
    return generate_multi_sheet_excel_response(
        [all, group, group_by_number, unit_price],
        [
            "发货表",
            "每日汇总",
            "按商品数量汇总",
            "去快递费单价",
        ],
        [
            style.sheet1_style,
            style.sheet2_style,
            style.sheet2_style,
            style.sheet2_style,
        ],
        default_name,
    )


@app.route("/wangjun-form", methods=["POST"])
def wangjun_form_aggregate_files_selected():
    fhd = save_files_to_temp_dir(request.files.getlist("fhd"))
    fhd = excel.merge_excel_files_from_paths(fhd)

    wangjun = excel.wangjun_filter_and_select_columns(fhd)

    current_date = datetime.now().strftime("%m月%d日")
    default_name = f"王君-{current_date}.xlsx"

    return generate_excel_response(wangjun, default_name)


@app.route("/wangjun-wechat-handle", methods=["POST"])
def wangjun_wechat_handle():
    wechat: str = request.form["wangjun-wechat"]

    # 获取日期和文件名
    today = date.today()
    filename = f"王君-快递信息表-{today.month}月{today.day}日.xlsx"
    default_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)

    # 解析微信信息
    new_headers = ["收件人姓名（必填）", "收件人手机（二选一）", "收件人电话（二选一）", "收件人地址（必填）", "备注"]
    rows = wechat.split("\n")
    data_list = [new_headers]

    for i, row in enumerate(rows):
        if len(row) > 20:
            # 这里您可能需要实现 decompose 函数来解析行，如您之前在 Electron 代码中所做
            mobile, name, addr = decompose(row)
            print([mobile, name, addr])
            if mobile and name and addr:
                jing = 1
                bao = 1
                qpz = False
                if i + 1 < len(rows):
                    matchJing = re.search(r"(\d+)斤", rows[i + 1])
                    matchBao = re.search(r"(\d+)包", rows[i + 1])
                    matchQPZ = re.search(r"切片竹", rows[i + 1])
                if matchJing:
                    jing = int(matchJing.group(1))
                if matchBao:
                    bao = int(matchBao.group(1))
                if matchQPZ:
                    qpz = True
                info = f"{500 * jing}g * {bao}"
                if qpz:
                    info = f"切片竹 {bao}包"
                data_list.append(
                    [
                        name,
                        mobile if len(mobile) == 11 else "",
                        mobile if len(mobile) != 11 else "",
                        addr,
                        info,
                    ]
                )

    # 将数据保存到 Excel 文件
    df = pd.DataFrame(data_list[1:], columns=new_headers)
    return generate_excel_response(df, filename)


@app.route("/shouhou-handle", methods=["POST"])
def shouhou_handle():
    data = request.get_json()  # 获取请求中的 JSON 数据

    # 提取数据
    shouhouOrder: str = data["shouhouOrder"]
    shouhouFileList: List[str] = data["shouhouFileList"]
    taobaoShouhouFileList: List[str] = data["taobaoShouhouFileList"]
    shouhouFanxianFileList: List[str] = data["shouhouFanxianFileList"]

    # 此处处理您的逻辑...

    # 返回响应
    return jsonify(
        {
            "result": "success",  # 或 'failure'
            "outputFile": "path_to_output_file",  # 或其他需要返回的数据
        }
    )


@app.route("/guixiangyuan-yuehuizhong", methods=["POST"])
def guixiangyuan_yuehuizhong():
    file_path = save_file_to_temp_dir(request.files.get("pdd"))
    try:
        orders_df = pd.read_csv(file_path, encoding="GBK")
    except UnicodeDecodeError:
        # 如果GBK编码失败，则尝试使用utf-8编码
        orders_df = pd.read_csv(file_path, encoding="utf-8")
    pdd = excel.pdd_yuehuizhong(orders_df)

    all = pd.concat([pdd], ignore_index=True)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for product_name, product_group in all.groupby("商品名称"):
            product_group.to_excel(writer, sheet_name=product_name, index=False)
    output.seek(0)

    # Return a Flask response
    return send_file(
        output, download_name=f"{get_previous_month_summary()}.xlsx", as_attachment=True
    )


def generate_excel_response(df: pd.DataFrame, filename: str):
    """
    Generates a Flask response containing the given DataFrame as an Excel file.

    Args:
    - df (pd.DataFrame): The DataFrame to be converted to Excel.
    - filename (str): The desired filename for the Excel file.

    Returns:
    - Flask response object with the Excel file.
    """

    # Convert the DataFrame to an Excel BytesIO object
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
    output.seek(0)

    # Return a Flask response
    return send_file(output, download_name=filename, as_attachment=True)


def apply_styles_to_worksheet(
    worksheet,
    workbook,
    styles: Dict[str, Any],
    row_number: int,
    apply_to_all_rows: bool = False,
):
    """
    应用样式到工作表的特定行。

    参数:
    - worksheet: xlsxwriter的worksheet对象。
    - workbook: xlsxwriter的workbook对象。
    - styles (Dict[str, Any]): 包含样式信息的字典。
    - row_number (int): 要应用样式的起始行号。
    - apply_to_all_rows (bool): 是否应用样式到所有行，从row_number开始。
    """
    # 设置行高
    height = styles.get("height")
    if height is not None:
        worksheet.set_row(row_number, height)

    # 设置单元格样式
    cell_styles = styles.get("styles", {})
    for col_letter, style_info in cell_styles.items():
        col_idx = pd.Index(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")).get_loc(col_letter)
        cell_format = workbook.add_format(
            {
                "bold": style_info.get("bold", False),
                "align": style_info.get("alignment", "general"),
            }
        )
        if apply_to_all_rows:
            worksheet.set_column(
                col_idx, col_idx, style_info.get("width", None), cell_format
            )
        else:
            worksheet.set_column(col_idx, col_idx, style_info.get("width", None))

def generate_multi_sheet_excel_response(
    df_list: List[pd.DataFrame],
    sheet_name_list: List[str],
    style_list: List[Dict[str, Any]],
    filename: str,
) -> Any:
    try:
        # 检查DataFrame列表、工作表名称列表和样式列表的长度是否相同
        if len(df_list) != len(sheet_name_list) or len(df_list) != len(style_list):
            raise ValueError("The lengths of df_list, sheet_name_list, and style_list must be the same.")

        # 将DataFrame列表转换为一个Excel BytesIO对象
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for df, sheet_name, styles in zip(df_list, sheet_name_list, style_list):
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                worksheet = writer.sheets[sheet_name]
                workbook = writer.book

                # 应用第一行的样式
                apply_styles_to_worksheet(
                    worksheet, workbook, styles.get("first_row", {}), 0
                )

                # 应用第二行及以下每一行的样式
                apply_styles_to_worksheet(
                    worksheet,
                    workbook,
                    styles.get("second_row", {}),
                    1,
                    apply_to_all_rows=True,
                )

        output.seek(0)

        # 返回一个Flask响应
        return send_file(output, download_name=filename, as_attachment=True)

    except Exception as e:
        logging.error(f"Error in generate_multi_sheet_excel_response: {str(e)}")
        return f"An error occurred: {str(e)}", 500

def _generate_multi_sheet_excel_response(
    df_list: List[pd.DataFrame], sheet_name_list: List[str], filename: str
) -> Any:
    """
    生成一个包含多个工作表的Excel文件作为Flask响应。

    参数:
    - df_list (List[DataFrame]): 包含多个DataFrame，每个DataFrame为一个工作表。
    - sheet_name_list (List[str]): 工作表的名称列表。
    - filename (str): Excel文件的期望文件名。

    返回:
    - Flask响应对象，其中包含Excel文件。
    """

    # 检查DataFrame列表和工作表名称列表的长度是否相同
    if len(df_list) != len(sheet_name_list):
        return "The length of df_list and sheet_name_list must be the same.", 400

    # 将DataFrame列表转换为一个Excel BytesIO对象
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for df, sheet_name in zip(df_list, sheet_name_list):
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)

    # 返回一个Flask响应
    return send_file(output, download_name=filename, as_attachment=True)


def open_file(filename):
    system_name = platform.system()
    if system_name == "Windows":
        os.startfile(filename)
    elif system_name == "Darwin":
        os.system(f'open "{filename}"')
    elif system_name == "Linux":
        os.system(f'xdg-open "{filename}"')
    else:
        print(f"Sorry, we don't support {system_name} yet.")


def decompose(string: str) -> dict:
    compose = {}

    search = [
        "收货地址",
        "详细地址",
        "地址",
        "收货人",
        "收件人",
        "收货",
        "所在地区",
        "邮编",
        "电话",
        "手机号码",
        "身份证号码",
        "身份证号",
        "身份证",
        "：",
        ":",
        "；",
        ";",
        "，",
        ",",
        "。",
    ]

    for s in search:
        string = string.replace(s, " ")

    string = re.sub(r"\s{1,}", " ", string)
    string = re.sub(r"0?(\d{3})-(\d{4})-(\d{4})([-_]\d{1,})", r"\1\2\3\4", string)

    match = re.search(r"\d{18}|\d{17}X", string, re.IGNORECASE)
    if match:
        compose["idn"] = match.group(0).upper()
        string = string.replace(match.group(0), "")

    match = re.search(r"\d{7,11}[\-_]\d{2,6}|\d{7,11}|\d{3,4}-\d{6,8}", string)
    if match:
        compose["mobile"] = match.group(0)
        string = string.replace(match.group(0), "")

    match = re.search(r"\d{6}", string)
    if match:
        compose["postcode"] = match.group(0)
        string = string.replace(match.group(0), "")

    string = string.strip()
    string = re.sub(r" {2,}", " ", string)

    split_arr = string.split(" ")
    if split_arr:
        compose["name"] = min(split_arr, key=len)
        string = string.replace(
            compose["name"], "", 1
        )  # replace only the first occurrence

    compose["addr"] = string.strip()

    return compose.get("mobile", ""), compose.get("name", ""), compose.get("addr", "")


# 获取可用端口的函数
def find_available_port(start_port, end_port):
    for port in range(start_port, end_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("127.0.0.1", port))
            if result != 0:
                return port
    return None


if __name__ == "__main__":
    # 查找可用端口
    start_port = 5000
    end_port = 30000  # 可以根据需要设置一个范围
    available_port = find_available_port(start_port, end_port)

    if available_port is not None:
        try:
            webbrowser.open(f"http://127.0.0.1:{available_port}/")
            app.run(port=available_port)
        finally:
            # 确保在程序结束时删除临时目录
            shutil.rmtree(tmpdirname)
    else:
        print("没有找到可用端口")


def get_previous_month_summary() -> str:
    """
    获取当前月份的前一个月，并返回格式化的字符串，例如“2023年09月电商汇总表”。

    Returns:
        str: 格式化的前一个月汇总表名称。
    """
    # 获取当前日期
    current_date = datetime.now()
    # 计算前一个月的最后一天
    first_day_of_current_month = current_date.replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    # 返回格式化的字符串
    return last_day_of_previous_month.strftime("%Y年%m月电商汇总表")
